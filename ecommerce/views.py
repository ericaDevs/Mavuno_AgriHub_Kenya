from django.shortcuts import render, redirect
from Products.models import Product

def home(request):
    products = Product.objects.filter(is_active=True).prefetch_related("images")[:10]
    return render(request, 'index.html', {'products' : products})

def aboutPage(request):
    return render(request, 'about.html')

def contactsPage(request):
    return render(request, 'contacts.html')

def servicesPage(request):
    return render(request, 'services.html')