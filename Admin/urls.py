from . import views
from django.urls import path

app_name = 'admin_dashboard'

urlpatterns = [
    path('overview/', views.overview, name='overview'),
    path('login/', views.login, name='login'),
    path('products/', views.products, name='products'),
    path('orders/', views.orders, name='orders'),
    path('inventory/', views.inventory, name='inventory'),
    path('sales/', views.sales, name='sales')
]