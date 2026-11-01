from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from Orders.models import Order
from Payments.models import MpesaPayment

from .forms import CustomUserCreationForm, LoginForm


def register(request):
    next_url = request.POST.get("next", "") or request.GET.get("next", "")
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Account created successfully!")
            login_url = reverse("authentication:login")
            if url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host()},
            ):
                login_url = f"{login_url}?{urlencode({'next': next_url})}"
            return redirect(login_url)
        messages.error(
            request,
            "An error occurred while creating the account, please check the form and try again.",
        )
    else:
        form = CustomUserCreationForm()

    return render(request, "Auth/register.html", {"form": form, "next": next_url})


def login(request):
    if request.user.is_authenticated:
        next_url = request.GET.get("next", "")
        if url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
            return redirect(next_url)
        return redirect("authentication:dashboard")

    form = LoginForm(request.POST if request.method == "POST" else None)
    next_url = request.POST.get("next", "") or request.GET.get("next", "")

    if request.method == "POST":
        if form.is_valid():
            User = get_user_model()
            user_record = User.objects.filter(
                username__iexact=form.cleaned_data["username"].strip(),
                email__iexact=form.cleaned_data["email"].strip(),
            ).first()
            user = None
            if user_record is not None:
                user = authenticate(
                    request,
                    username=user_record.get_username(),
                    password=form.cleaned_data["password"],
                )

            if user is not None:
                auth_login(request, user)
                messages.success(request, "Logged in successfully!")
                if url_has_allowed_host_and_scheme(
                    next_url,
                    allowed_hosts={request.get_host()},
                ):
                    return redirect(next_url)
                return redirect("authentication:dashboard")

            messages.error(request, "Invalid credentials, please check and try again!")
        else:
            messages.error(request, "All fields are required!")

    return render(
        request,
        "Auth/login.html",
        {"form": form, "next": next_url},
    )


@login_required(login_url="authentication:login")
def dashboard(request):
    orders = Order.objects.filter(customer=request.user)
    active_orders = orders.filter(
        status__in=[
            Order.Status.PAID,
            Order.Status.PROCESSING,
            Order.Status.SHIPPED,
        ]
    )
    recent_orders = (
        orders.select_related("delivery")
        .prefetch_related("items")
        .order_by("-created_time")[:5]
    )
    total_spent = (
        orders.exclude(status=Order.Status.CANCELLED)
        .aggregate(total=Sum("total_amount"))["total"]
        or 0
    )
    pending_payments = MpesaPayment.objects.filter(
        customer=request.user,
        status=MpesaPayment.Status.PENDING,
    ).count()

    return render(
        request,
        "customer_dashboard/overview.html",
        {
            "order_count": orders.count(),
            "total_spent": total_spent,
            "active_order_count": active_orders.count(),
            "pending_payment_count": pending_payments,
            "recent_orders": recent_orders,
            "display_name": request.user.get_full_name() or request.user.username,
        },
    )


@login_required
def logout(request):
    auth_logout(request)
    messages.success(request, "Logged out successfully!")
    return redirect("authentication:login")
