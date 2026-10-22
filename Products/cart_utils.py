def get_session_cart(request):
    stored_cart = request.session.get("cart", {})
    if not isinstance(stored_cart, dict):
        return {}

    cart = {}
    for product_id, quantity in stored_cart.items():
        try:
            product_id = int(product_id)
            quantity = int(quantity)
        except (TypeError, ValueError):
            continue
        if product_id > 0 and quantity > 0:
            cart[str(product_id)] = quantity
    return cart
