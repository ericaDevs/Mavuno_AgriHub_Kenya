from functools import wraps

from django.contrib import messages
from django.contrib.auth.hashers import check_password
from django.db import transaction
from django.shortcuts import get_object_or_404, render, redirect

from .forms import CustomUserCreationForm, LoginForm
from .models import Admins
from Products.forms import ProductForm
from Products.models import Product


def admin_required(view_func):
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if not request.session.get("admin_id"):
            return redirect("admin:login")
        return view_func(request, *args, **kwargs)

    return wrapped_view


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


# Product dashboard
def _products_page(request, create_form=None, editing_product=None, edit_form=None):
    products = Product.objects.prefetch_related("images")
    search = request.GET.get("q", "").strip()
    category = request.GET.get("category", "")
    if search:
        products = products.filter(name__icontains=search)
    if category:
        products = products.filter(product_category=category)

    for product in products:
        product.management_form = (
            edit_form
            if editing_product and product.pk == editing_product.pk
            else ProductForm(instance=product)
        )

    context = {
        "products": products,
        "categories": Product.Category.choices,
        "selected_category": category,
        "search": search,
        "total_products": Product.objects.count(),
        "active_products": Product.objects.filter(is_active=True).count(),
        "out_of_stock_products": Product.objects.filter(stock_quantity=0).count(),
        "create_form": create_form or ProductForm(),
        "editing_product": editing_product,
    }
    return render(request, "Dashboard/products.html", context)


@admin_required
def product_management(request):
    return _products_page(request)


@admin_required
def product_create(request):
    if request.method != "POST":
        return redirect("admin:products")

    form = ProductForm(request.POST, request.FILES)
    if form.is_valid():
        with transaction.atomic():
            product = form.save()
            for image in form.cleaned_data["images"]:
                product.images.create(image=image)
        messages.success(request, f'"{product.name}" was added to the catalog.')
        return redirect("admin:products")
    return _products_page(request, create_form=form)


@admin_required
def product_update(request, product_id):
    product = get_object_or_404(Product.objects.prefetch_related("images"), pk=product_id)
    if request.method != "POST":
        return redirect("admin:products")

    form = ProductForm(request.POST, request.FILES, instance=product)
    if form.is_valid():
        with transaction.atomic():
            product = form.save()
            removed_images = list(form.cleaned_data["remove_images"])
            for product_image in removed_images:
                product_image.image.delete(save=False)
                product_image.delete()
            for image in form.cleaned_data["images"]:
                product.images.create(image=image)
        messages.success(request, f'"{product.name}" was updated.')
        return redirect("admin:products")
    return _products_page(request, editing_product=product, edit_form=form)


@admin_required
def product_delete(request, product_id):
    if request.method != "POST":
        return redirect("admin:products")

    product = get_object_or_404(Product.objects.prefetch_related("images"), pk=product_id)
    name = product.name
    for product_image in product.images.all():
        product_image.image.delete(save=False)
    product.delete()
    messages.success(request, f'"{name}" was removed from the catalog.')
    return redirect("admin:products")







@admin_required
def overview(request):
    return render(request, "Dashboard/overview.html")


@admin_required
def orders(request):
    return render(request, "Dashboard/orders.html")


@admin_required
def inventory(request):
    return render(request, "Dashboard/inventory.html")


@admin_required
def sales(request):
    return render(request, "Dashboard/sales.html")
