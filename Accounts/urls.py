from . import views
from django.urls import path

app_name = 'authentication'

urlpatterns = [
    path('register/', views.register, name = 'register'),
    path('login/', views.login, name='login'),
    path('overview/', views.overview, name='overview'),
    path('products/', views.products, name='products'),
    path('orders/', views.orders, name='orders'),
    path('inventory/', views.inventory, name='inventory'),
    path('sales/', views.sales, name='sales')
]