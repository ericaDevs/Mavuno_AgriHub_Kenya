from decimal import Decimal
import json
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt

from Orders.models import Order, OrderItem
from Products.cart_utils import get_session_cart
from Products.models import Product
from .forms import CustomerDeliveryInfor
from .models import Delivery_infor, MpesaPayment
from .daraja import normalize_phone, stk_push, stk_query, DarajaError


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
    """
    Validates delivery details and advances user to payment without creating DB records prematurely.
    """
    delivery_data = request.session.get("checkout_delivery")
    cart = get_session_cart(request)
    if not isinstance(delivery_data, dict) or not delivery_data:
        messages.error(request, "Enter your delivery details before proceeding to payment.")
        return redirect("payments:checkout")
    if not cart:
        messages.error(request, "Your cart is empty. Add products before proceeding.")
        return redirect("products:cart")

    return redirect(f"{reverse('payments:checkout')}#payment")


def _create_order_for_payment(payment):
    """
    Creates Order, OrderItem records, and Delivery_infor atomically
    ONLY when payment is confirmed and successful.
    """
    if payment.order:
        return payment.order

    cart = payment.cart_snapshot or {}
    delivery_data = payment.delivery_snapshot or {}

    products = list(
        Product.objects.select_for_update()
        .filter(pk__in=cart.keys())
        .prefetch_related("images")
    )
    products_by_id = {str(product.pk): product for product in products}

    subtotal = sum(
        (
            products_by_id[product_id].price_per_unit * quantity
            for product_id, quantity in cart.items()
            if product_id in products_by_id
        ),
        Decimal("0.00"),
    )
    total_amount = Decimal(payment.amount) if payment.amount else (subtotal + DELIVERY_FEE)

    order = Order.objects.create(
        customer=payment.customer,
        item_subtotal=subtotal,
        delivery_fee=DELIVERY_FEE,
        total_amount=total_amount,
        status=Order.Status.PAID,
    )

    order_items = []
    for product_id, quantity in cart.items():
        if product_id in products_by_id:
            product = products_by_id[product_id]
            product.stock_quantity = max(0, product.stock_quantity - quantity)
            product.save(update_fields=["stock_quantity"])
            order_items.append(
                OrderItem(
                    order=order,
                    product=product,
                    product_name=product.name,
                    unit_price=product.price_per_unit,
                    quantity=quantity,
                )
            )
    if order_items:
        OrderItem.objects.bulk_create(order_items)

    Delivery_infor.objects.create(
        order=order,
        full_name=delivery_data.get("full_name", ""),
        phone_number=delivery_data.get("phone", payment.phone),
        email_address=delivery_data.get("email", ""),
        delivery_Address=delivery_data.get("delivery_address", ""),
        delivery_note=delivery_data.get("delivery_notes", ""),
    )

    payment.order = order
    payment.save(update_fields=["order"])
    return order


# PAY WITH MPESA
@login_required(login_url="authentication:login")
@require_POST
def initiate_payment(request, order_id=None):
    try:
        body = json.loads(request.body or "{}")
    except ValueError:
        return JsonResponse({"ok": False, "message": "Invalid request body."}, status=400)

    if not isinstance(body, dict):
        return JsonResponse({"ok": False, "message": "Invalid request body."}, status=400)

    order = None
    if order_id:
        order = get_object_or_404(Order, pk=order_id, customer=request.user)
        amount = int(order.total_amount)
        cart = {}
        delivery_data = {
            "phone": order.delivery.phone_number if hasattr(order, "delivery") else "",
            "full_name": order.delivery.full_name if hasattr(order, "delivery") else "",
            "delivery_address": order.delivery.delivery_Address if hasattr(order, "delivery") else "",
        }
    else:
        cart = get_session_cart(request)
        delivery_data = request.session.get("checkout_delivery", {})
        if not cart:
            return JsonResponse({"ok": False, "message": "Your cart is empty. Add products before paying."}, status=400)
        if not delivery_data or not isinstance(delivery_data, dict):
            return JsonResponse({"ok": False, "message": "Please save your delivery information before paying."}, status=400)

        # Validate stock
        products = list(Product.objects.filter(pk__in=cart.keys(), is_active=True))
        products_by_id = {str(product.pk): product for product in products}
        unavailable = [
            product_id
            for product_id, quantity in cart.items()
            if product_id not in products_by_id or products_by_id[product_id].stock_quantity < quantity
        ]
        if unavailable:
            return JsonResponse(
                {
                    "ok": False,
                    "message": "One or more products in your cart are no longer available in the requested quantity. Please review your cart.",
                },
                status=400,
            )

        subtotal = sum(
            (products_by_id[product_id].price_per_unit * quantity for product_id, quantity in cart.items()),
            Decimal("0.00"),
        )
        total = subtotal + DELIVERY_FEE
        amount = int(total)

    if amount <= 0:
        return JsonResponse({"ok": False, "message": "Total amount must be greater than zero."}, status=400)

    raw_phone = body.get("phone") or delivery_data.get("phone", "")
    try:
        phone = normalize_phone(raw_phone)
    except DarajaError as e:
        return JsonResponse({"ok": False, "message": str(e)}, status=400)

    # Check for recent existing PENDING payment for this customer
    pending_payment = MpesaPayment.objects.filter(
        customer=request.user,
        status=MpesaPayment.Status.PENDING,
    ).order_by("-created_at").first()

    if pending_payment:
        if (timezone.now() - pending_payment.created_at).total_seconds() < 90:
            return JsonResponse(
                {
                    "ok": True,
                    "payment_id": pending_payment.pk,
                    "status_url": reverse("payments:payment_status", args=[pending_payment.pk]),
                    "message": "A payment prompt was already sent to your phone. Please check your phone for the M-Pesa PIN prompt.",
                }
            )

    account_ref = f"M{request.user.pk}"
    try:
        res = stk_push(phone, amount, account_ref, "Mavuno AgriHub")
    except DarajaError as e:
        return JsonResponse({"ok": False, "message": str(e)}, status=400)

    if res.get("ResponseCode") != "0":
        return JsonResponse({"ok": False, "message": res.get("ResponseDescription") or "Payment request was not accepted by M-Pesa."}, status=400)

    if not res.get("MerchantRequestID") or not res.get("CheckoutRequestID"):
        return JsonResponse({"ok": False, "message": "M-Pesa returned an incomplete response. Please try again."}, status=502)

    payment = MpesaPayment.objects.create(
        customer=request.user,
        order=order if order_id else None,
        phone=phone,
        amount=amount,
        merchant_request_id=res["MerchantRequestID"],
        checkout_request_id=res["CheckoutRequestID"],
        cart_snapshot=cart,
        delivery_snapshot=delivery_data,
        status=MpesaPayment.Status.PENDING,
    )

    return JsonResponse(
        {
            "ok": True,
            "payment_id": payment.pk,
            "status_url": reverse("payments:payment_status", args=[payment.pk]),
            "message": res.get("CustomerMessage") or "M-Pesa prompt sent. Please check your phone.",
        }
    )


STATUS_MAP = {
    0: MpesaPayment.Status.SUCCESS,
    1032: MpesaPayment.Status.CANCELLED,
    1037: MpesaPayment.Status.TIMEOUT,
}


def _apply_result(payment, code, desc, items=None, raw=None, request=None):
    with transaction.atomic():
        p = MpesaPayment.objects.select_for_update().get(pk=payment.pk)
        if p.status != MpesaPayment.Status.PENDING:
            return p

        p.result_code = code
        p.result_desc = desc
        p.status = STATUS_MAP.get(code, MpesaPayment.Status.FAILED)

        if raw is not None:
            p.raw_callback = raw

        if code == 0:
            if items:
                meta = {i["Name"]: i.get("Value") for i in items if "Name" in i}
                p.mpesa_receipt = meta.get("MpesaReceiptNumber", "")
                if meta.get("Amount") and int(meta["Amount"]) != p.amount:
                    p.status = MpesaPayment.Status.FAILED
                    p.result_desc = "Amount mismatch - review manually"

            if p.status == MpesaPayment.Status.SUCCESS:
                order = _create_order_for_payment(p)
                p.order = order

        p.save()

    if request is not None and p.status == MpesaPayment.Status.SUCCESS:
        request.session.pop("cart", None)
        request.session.pop("checkout_delivery", None)

    return p


# RESPONSE FROM MPESA DARAJA
@csrf_exempt
@require_POST
def mpesa_callback(request):
    try:
        raw = json.loads(request.body)
        cb = raw["Body"]["stkCallback"]
        payment = MpesaPayment.objects.get(checkout_request_id=cb["CheckoutRequestID"])
    except (KeyError, ValueError, MpesaPayment.DoesNotExist):
        return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})

    items = cb.get("CallbackMetadata", {}).get("Item", [])
    _apply_result(payment, cb["ResultCode"], cb["ResultDesc"], items, raw)
    return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})


# QUERY TRANSACTION STATUS
@login_required(login_url="authentication:login")
@require_GET
def payment_status(request, payment_id):
    p = get_object_or_404(MpesaPayment, pk=payment_id, customer=request.user)

    if p.status == MpesaPayment.Status.PENDING:
        try:
            q = stk_query(p.checkout_request_id)
            if "ResultCode" in q:
                _apply_result(p, int(q["ResultCode"]), q.get("ResultDesc", ""), raw=q, request=request)
                p.refresh_from_db()
        except DarajaError:
            pass

    if p.status == MpesaPayment.Status.SUCCESS:
        if request:
            request.session.pop("cart", None)
            request.session.pop("checkout_delivery", None)

        success_url = reverse(
            "orders:order_confirmation",
            kwargs={"order_reference": p.order.order_reff},
        ) if p.order else reverse("products:products")

        return JsonResponse(
            {
                "status": "SUCCESS",
                "message": "Payment confirmed! Your order has been placed.",
                "receipt": p.mpesa_receipt,
                "success_url": success_url,
            }
        )

    elif p.status == MpesaPayment.Status.CANCELLED:
        return JsonResponse(
            {
                "status": "CANCELLED",
                "message": "Payment was cancelled. You can retry with M-Pesa whenever you are ready.",
                "receipt": "",
            }
        )

    elif p.status in [MpesaPayment.Status.FAILED, MpesaPayment.Status.TIMEOUT]:
        return JsonResponse(
            {
                "status": p.status,
                "message": p.result_desc or "Payment could not be completed. Please try again.",
                "receipt": "",
            }
        )

    else:
        return JsonResponse(
            {
                "status": "PENDING",
                "message": "Waiting for payment confirmation. Please enter your PIN on your phone.",
                "receipt": "",
            }
        )
