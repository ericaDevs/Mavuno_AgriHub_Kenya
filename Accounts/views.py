from django.contrib import messages
from django.shortcuts import render, redirect
from .forms import CustomUserCreationForm, LoginForm
from django.contrib.auth import login as auth_login, authenticate, logout as auth_logout
from django.contrib.auth.decorators import login_required

# USER REGISTRATION VIEW
def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Account created successfully!")
            return redirect('authentication:login')
        else:
            messages.error(request, 'An error occurred while creating the account, please check the form and try again.')
            return render(request, 'Auth/register.html', {'form': form})
    form = CustomUserCreationForm()
    return render(request, 'Auth/register.html', {'form' : form})


# ADMIN AUTHORIZATION & AUTHENTICATION
def login(request):
    if request.user.is_authenticated:
        return redirect('authentication:overview')

    form = LoginForm(request.POST if request.method == "POST" else None)

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "")
        password = request.POST.get("password", "")

        if not username or not email or not password:
            messages.error(request, "All fields are required!")
            return render(request, "Auth/login.html", {"form": form})

        user = authenticate(request, username = username, email=email, password = password)
        
        if user is None:
            from django.contrib.auth import get_user_model
            UserModel = get_user_model()
            try:
                # Try finding user by email or case-insensitive username
                user_obj = UserModel.objects.filter(email__iexact=username).first()
                if not user_obj:
                    user_obj = UserModel.objects.filter(username__iexact=username).first()
                if user_obj:
                    user = authenticate(request, username=user_obj.username, password=password)
            except Exception:
                pass

        if user is not None:
            auth_login(request, user)
            messages.success(request, "Logged in successfully!")
            return redirect('authentication:overview')
        messages.error(request, "Invalid credentials, please check and try again!")
        return render(request, "Auth/login.html", {"form": form})
    
    return render(request, 'Auth/login.html', {"form": form})


# LOGOUT
@login_required
def logout(request):
    auth_logout(request)
    messages.success(request, "Logged out successfully!")
    return redirect('authentication:login')




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