from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from .models import Order


# Create your views here.
@login_required(login_url="authentication:login")
def order_confirmation(request, order_reference):
    order = get_object_or_404(
        Order.objects.prefetch_related("items").select_related("delivery"),
        order_reff=order_reference,
        customer=request.user,
    )
    return render(request, "orderConfirmation.html", {"order": order})