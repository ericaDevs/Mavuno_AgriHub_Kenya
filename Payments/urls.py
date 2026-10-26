from django.urls import path
from . import views

app_name = "payments"

urlpatterns = [
    path("", views.checkout_page, name="checkout"),
    path("orders/confirm/", views.confirm_order, name="confirm_order"),
    path("paywithmpesa/", views.pay_with_mpesa, name = 'mpesa')
]