from functools import wraps

from django.contrib import messages
from django.contrib.auth.hashers import check_password
from django.shortcuts import render, redirect

from .forms import CustomUserCreationForm, LoginForm
from .models import Admins


def register(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Account created successfully!")
            return redirect("admin:login")
        messages.error(
            request,
            "An error occurred while creating the account, please check the form and try again.",
        )
        return render(request, "Auth_d/register.html", {"form": form})

    form = CustomUserCreationForm()
    return render(request, "Auth_d/register.html", {"form": form})


def login(request):
    if request.session.get("admin_id"):
        return redirect("admin:overview")

    form = LoginForm(request.POST if request.method == "POST" else None)
    if request.method == "POST":
        if not form.is_valid():
            messages.error(request, "All fields are required!")
            return render(request, "Auth_d/login.html", {"form": form})

        username = form.cleaned_data["username"].strip()
        email = form.cleaned_data["email"].strip()
        password = form.cleaned_data["password"]
        admin = Admins.objects.filter(
            username__iexact=username,
            email__iexact=email,
        ).first()

        if admin is not None and check_password(password, admin.password):
            request.session.cycle_key()
            request.session["admin_id"] = admin.pk
            messages.success(request, "Logged in successfully!")
            return redirect("admin:overview")

        messages.error(request, "Invalid credentials, please check and try again!")

    return render(request, "Auth_d/login.html", {"form": form})


def logout(request):
    request.session.pop("admin_id", None)
    messages.success(request, "Logged out successfully!")
    return redirect("admin:login")


def admin_required(view_func):
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if not request.session.get("admin_id"):
            return redirect("admin:login")
        return view_func(request, *args, **kwargs)

    return wrapped_view


@admin_required
def overview(request):
    return render(request, "Dashboard/overview.html")


@admin_required
def products(request):
    return render(request, "Dashboard/products.html")


@admin_required
def orders(request):
    return render(request, "Dashboard/orders.html")


@admin_required
def inventory(request):
    return render(request, "Dashboard/inventory.html")


@admin_required
def sales(request):
    return render(request, "Dashboard/sales.html")
