from django.shortcuts import render, redirect

def home(request):
    return render(request, 'index.html')

def aboutPage(request):
    return render(request, 'about.html')

def contactsPage(request):
    return render(request, 'contacts.html')

def servicesPage(request):
    return render(request, 'services.html')