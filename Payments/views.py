from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from Orders.models import Order, OrderItem
from Products.cart_utils import get_session_cart
from Products.models import Product
from .forms import CustomerDeliveryInfor
from .models import Delivery_infor


DELIVERY_FEE = Decimal("0.00")


def _checkout_context(request, form=None):
    cart = get_session_cart(request)
    products = Product.objects.filter(
        pk__in=cart.keys(),
        is_active=True,
    ).prefetch_related("images")
    products_by_id = {str(product.pk): product for product in products}

    items = []
    subtotal = Decimal("0.00")
    item_count = 0
    available_cart = {}
    for product_id, quantity in cart.items():
        product = products_by_id.get(product_id)
        if product is None or product.stock_quantity == 0:
            messages.warning(
                request,
                "An unavailable product was removed from your cart.",
            )
            continue

        if quantity > product.stock_quantity:
            quantity = product.stock_quantity
            messages.info(
                request,
                f'Quantity for "{product.name}" was adjusted to current stock.',
            )

        available_cart[product_id] = quantity
        line_total = product.price_per_unit * quantity
        subtotal += line_total
        item_count += quantity
        items.append(
            {
                "product": product,
                "quantity": quantity,
                "line_total": line_total,
                "image": product.images.first(),
            }
        )

    if available_cart != cart:
        request.session["cart"] = available_cart

    delivery_data = request.session.get("checkout_delivery", {})
    if not isinstance(delivery_data, dict):
        delivery_data = {}

    return {
        "items": items,
        "subtotal": subtotal,
        "delivery_fee": DELIVERY_FEE,
        "total": subtotal + DELIVERY_FEE,
        "item_count": item_count,
        "form": form or CustomerDeliveryInfor(initial=delivery_data),
        "delivery_data": delivery_data,
    }


@login_required(login_url="authentication:login")
def checkout_page(request):
    context = _checkout_context(request)
    if not context["items"]:
        messages.info(request, "Add available products to your cart before checkout.")
        return redirect("products:cart")

    # Saving delivery information
    if request.method == "POST":
        form = CustomerDeliveryInfor(request.POST)
        if form.is_valid():
            request.session["checkout_delivery"] = form.cleaned_data
            messages.success(request, "Delivery details saved. Review your order below.")
            return redirect(f"{reverse('payments:checkout')}#order-review")
        context = _checkout_context(request, form=form)

    return render(request, "checkOut.html", context)




@login_required(login_url="authentication:login")
@require_POST
def confirm_order(request):
    delivery_data = request.session.get("checkout_delivery")
    cart = get_session_cart(request)
    if not isinstance(delivery_data, dict) or not delivery_data:
        messages.error(request, "Enter your delivery details before confirming the order.")
        return redirect("payments:checkout")
    if not cart:
        messages.error(request, "Your cart is empty. Add products before confirming.")
        return redirect("products:cart")

    with transaction.atomic():
        products = list(
            Product.objects.select_for_update()
            .filter(pk__in=cart.keys(), is_active=True)
            .prefetch_related("images")
        )
        products_by_id = {str(product.pk): product for product in products}
        unavailable = [
            product_id
            for product_id, quantity in cart.items()
            if product_id not in products_by_id
            or products_by_id[product_id].stock_quantity < quantity
        ]
        if unavailable:
            messages.error(
                request,
                "One or more products are no longer available in the requested quantity. Review your cart and try again.",
            )
            return redirect("payments:checkout")

        subtotal = sum(
            (
                products_by_id[product_id].price_per_unit * quantity
                for product_id, quantity in cart.items()
            ),
            Decimal("0.00"),
        )
        order = Order.objects.create(
            customer=request.user,
            item_subtotal=subtotal,
            delivery_fee=DELIVERY_FEE,
            total_amount=subtotal + DELIVERY_FEE,
        )
        OrderItem.objects.bulk_create(
            [
                OrderItem(
                    order=order,
                    product=products_by_id[product_id],
                    product_name=products_by_id[product_id].name,
                    unit_price=products_by_id[product_id].price_per_unit,
                    quantity=quantity,
                )
                for product_id, quantity in cart.items()
            ]
        )
        Delivery_infor.objects.create(
            order=order,
            full_name=delivery_data["full_name"],
            phone_number=delivery_data["phone"],
            email_address=delivery_data.get("email", ""),
            delivery_Address=delivery_data["delivery_address"],
            delivery_note=delivery_data.get("delivery_notes", ""),
        )

    request.session.pop("cart", None)
    request.session.pop("checkout_delivery", None)
    messages.success(request, "Your order was received and is awaiting payment.")
    return redirect(
        "orders:order_confirmation",
        order_reference=order.order_reff,
    )




# PAY WITH MPESA
def pay_with_mpesa(request):
    return render(request, "mpesa.html")