from django.shortcuts import render

def login(request):
    return render(request, 'Dashboard/overview.html')

def overview(request):
    return render(request, 'Dashboard/overview.html')

def products(request):
    return render(request, 'Dashboard/products.html')

def orders(request):
    return render(request, 'Dashboard/orders.html')

def inventory(request):
    return render(request, 'Dashboard/inventory.html')

def sales(request):
    return render(request, 'Dashboard/sales.html')