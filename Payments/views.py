from django.shortcuts import render

# Create your views here.
def checkout_page(request):
    return render(request, 'checkOut.html')