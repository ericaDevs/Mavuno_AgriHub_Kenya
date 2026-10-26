from django.urls import path
from . import views

app_name = "orders"

urlpatterns = [
    path("<str:order_reference>/confirmation/", views.order_confirmation, name="order_confirmation"),
]
