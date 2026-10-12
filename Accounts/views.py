from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django import forms

# USER REGISTRATION VIEW
class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('email',)


def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.info(request, "Account created successully, please log in with your details!")
            return redirect('authentication:login')
        else:
            messages.error(request, 'An error occurred while creating the account, please check the form and try submitting again.')
            return redirect('authentication:register')
    form = CustomUserCreationForm()
    return render(request, 'Auth/register.html', {'form' : form})





# USER LOGIN VIEW
def login(request):
    return render(request, 'Auth/login.html')


# Admin Views
def overview(request):
    return render(request, 'Admin/overview.html')

def products(request):
    return render(request, 'Admin/products.html')

def orders(request):
    return render(request, 'Admin/orders.html')

def inventory(request):
    return render(request, 'Admin/inventory.html')

def sales(request):
    return render(request, 'Admin/sales.html')

# Customer Views