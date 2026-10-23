from django.urls import path
from . import views

app_name = "payments"

urlpatterns = [
    path("", views.checkout_page, name="checkout"),
    path("orders/confirm/", views.confirm_order, name="confirm_order"),
    path(
        "orders/<str:order_reference>/confirmation/",
        views.order_confirmation,
        name="order_confirmation",
    ),
]