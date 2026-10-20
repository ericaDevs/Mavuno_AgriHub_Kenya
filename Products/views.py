from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render

from Admin.views import admin_required

from .forms import ProductForm
from .models import Product


# CATALOG PAGE VIEW
def catalog(request):
    search = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()
    products = Product.objects.filter(is_active=True).prefetch_related("images")
    if search:
        products = products.filter(Q(name__icontains=search) | Q(description__icontains=search))
    if category:
        products = products.filter(product_category=category)

    category_counts = dict(
        Product.objects.filter(is_active=True)
        .values_list("product_category")
        .annotate(count=Count("pk"))
    )
    categories = [
        {
            "value": value,
            "label": label,
            "count": category_counts.get(value, 0),
        }
        for value, label in Product.Category.choices
    ]
    context = {
        "products": products,
        "categories": categories,
        "search": search,
        "selected_category": category,
        "selected_category_label": dict(Product.Category.choices).get(category, ""),
        "total_products": products.count(),
        "total_catalog_products": Product.objects.filter(is_active=True).count(),
    }
    return render(request, "Cartegories/catalog.html", context)



# DASHBOARD PROJECTS PAGE
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