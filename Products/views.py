from decimal import Decimal

from django.contrib import messages
from django.contrib.messages import get_messages
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.template.loader import render_to_string
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .cart_utils import get_session_cart
from .models import Product


# CATALOG PAGE VIEW
def catalog(request):
    search = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()
    products = Product.objects.filter(is_active=True).prefetch_related("images")
    if search:
        products = products.filter(Q(name__icontains=search) | Q(description__icontains=search))
    if category:
        products = products.filter(product_category=category)

    category_counts = dict(
        Product.objects.filter(is_active=True)
        .values_list("product_category")
        .annotate(count=Count("pk"))
    )
    categories = [
        {
            "value": value,
            "label": label,
            "count": category_counts.get(value, 0),
        }
        for value, label in Product.Category.choices
    ]
    context = {
        "products": products,
        "categories": categories,
        "search": search,
        "selected_category": category,
        "selected_category_label": dict(Product.Category.choices).get(category, ""),
        "total_products": products.count(),
        "total_catalog_products": Product.objects.filter(is_active=True).count(),
    }
    return render(request, "Cartegories/catalog.html", context)


def product_detail(request, pk):
    product = get_object_or_404(
        Product.objects.filter(is_active=True).prefetch_related("images"),
        pk=pk,
    )
    return render(request, "Processes/productDetail.html", {"product": product})


def _cart_context(request):
    cart = get_session_cart(request)
    products = Product.objects.filter(
        pk__in=cart.keys(),
        is_active=True,
    ).prefetch_related("images")
    products_by_id = {str(product.pk): product for product in products}

    items = []
    subtotal = Decimal("0.00")
    item_count = 0
    updated_cart = {}
    cart_changed = False

    for product_id, quantity in cart.items():
        product = products_by_id.get(product_id)
        if product is None or product.stock_quantity == 0:
            cart_changed = True
            continue

        if quantity > product.stock_quantity:
            quantity = product.stock_quantity
            cart_changed = True
            messages.info(
                request,
                f'Quantity for "{product.name}" was adjusted to current available stock.',
            )

        line_total = product.price_per_unit * quantity
        subtotal += line_total
        item_count += quantity
        updated_cart[product_id] = quantity
        items.append(
            {
                "product": product,
                "quantity": quantity,
                "line_total": line_total,
                "image": product.images.first(),
            }
        )

    if cart_changed or cart != updated_cart:
        request.session["cart"] = updated_cart

    return {"items": items, "subtotal": subtotal, "item_count": item_count}


def _is_cart_ajax(request):
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


def _cart_ajax_response(request):
    context = _cart_context(request)
    messages_for_response = [
        {"text": str(message), "tags": message.tags}
        for message in get_messages(request)
    ]
    cart_html = render_to_string(
        "Processes/partials/cartContent.html",
        context,
        request=request,
    )
    return JsonResponse(
        {
            "cart_html": cart_html,
            "item_count": context["item_count"],
            "messages": messages_for_response,
        }
    )


def cart_page(request):
    return render(request, "Processes/cartPage.html", _cart_context(request))


@require_POST
def cart_add(request, pk):
    product = get_object_or_404(Product, pk=pk, is_active=True)
    detail_url = reverse("products:detail", args=[product.pk])
    next_url = request.POST.get("next", "")
    if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        next_url = ""

    if product.stock_quantity == 0:
        messages.error(request, f'"{product.name}" is currently out of stock.')
        if _is_cart_ajax(request):
            return _cart_ajax_response(request)
        return redirect(next_url or detail_url)

    try:
        quantity = int(request.POST.get("quantity", "1"))
    except (TypeError, ValueError):
        messages.error(request, "Enter a valid quantity.")
        if _is_cart_ajax(request):
            return _cart_ajax_response(request)
        return redirect(next_url or detail_url)

    if quantity < 1:
        messages.error(request, "Quantity must be at least one.")
        if _is_cart_ajax(request):
            return _cart_ajax_response(request)
        return redirect(next_url or detail_url)

    cart = get_session_cart(request)
    product_key = str(product.pk)
    requested_quantity = cart.get(product_key, 0) + quantity
    cart[product_key] = min(requested_quantity, product.stock_quantity)
    request.session["cart"] = cart

    if requested_quantity > product.stock_quantity:
        messages.info(
            request,
            f'Only {product.stock_quantity} of "{product.name}" are currently available.',
        )
    else:
        messages.success(request, f'"{product.name}" was added to your cart.')
    if _is_cart_ajax(request):
        return _cart_ajax_response(request)
    return redirect(next_url or "products:cart")


@require_POST
def cart_update(request, pk):
    product = get_object_or_404(Product, pk=pk, is_active=True)
    cart = get_session_cart(request)
    product_key = str(product.pk)

    if product_key not in cart:
        messages.error(request, "That product is no longer in your cart.")
        if _is_cart_ajax(request):
            return _cart_ajax_response(request)
        return redirect("products:cart")

    try:
        adjustment = int(request.POST.get("adjustment", ""))
    except (TypeError, ValueError):
        messages.error(request, "That quantity adjustment is invalid.")
        if _is_cart_ajax(request):
            return _cart_ajax_response(request)
        return redirect("products:cart")

    if adjustment not in (-1, 1):
        messages.error(request, "That quantity adjustment is invalid.")
    elif product.stock_quantity == 0:
        cart.pop(product_key)
        request.session["cart"] = cart
        messages.error(request, f'"{product.name}" is now out of stock and was removed.')
    elif adjustment == 1 and cart[product_key] >= product.stock_quantity:
        messages.info(request, f'Only {product.stock_quantity} of "{product.name}" are available.')
    else:
        quantity = cart[product_key] + adjustment
        if quantity == 0:
            cart.pop(product_key)
        else:
            cart[product_key] = quantity
        request.session["cart"] = cart
        messages.success(request, "Your cart was updated.")
    if _is_cart_ajax(request):
        return _cart_ajax_response(request)
    return redirect("products:cart")


@require_POST
def cart_remove(request, pk):
    cart = get_session_cart(request)
    cart.pop(str(pk), None)
    request.session["cart"] = cart
    messages.success(request, "The item was removed from your cart.")
    if _is_cart_ajax(request):
        return _cart_ajax_response(request)
    return redirect("products:cart")