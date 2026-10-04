from django.shortcuts import render, redirect

def home(request):
    return render(request, 'home/index.html')

def catalogPage(request):
    return render(request, 'home/catalog.html')

def aboutPage(request):
    return render(request, 'support/about.html')

def contactsPage(request):
    return render(request, 'support/contacts.html')

def servicesPage(request):
    return render(request, 'home/services.html')