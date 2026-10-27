# payments/urls.py
from django.urls import path
from . import views

app_name = "payments"

urlpatterns = [
    path("checkout/", views.checkout_page, name="checkout"),
    path("checkout/confirm/", views.confirm_order, name="confirm_order"),
    path("mpesa/pay/<int:order_id>/", views.initiate_payment, name = "mpesa"),
    path("mpesa/callback/", views.mpesa_callback),
    path("mpesa/status/<int:payment_id>/", views.payment_status),
]
