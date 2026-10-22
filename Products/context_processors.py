from .cart_utils import get_session_cart


def cart_summary(request):
    cart = get_session_cart(request)
    return {"cart_item_count": sum(cart.values())}
