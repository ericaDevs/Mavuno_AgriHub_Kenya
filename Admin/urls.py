from . import views
from Products import views as product_views
from django.urls import path

app_name = 'admin'

urlpatterns = [
    path('', views.login, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.logout, name='logout'),
    path('overview/', views.overview, name='overview'),
    path('products/', product_views.product_management, name='products'),
    path('products/add/', product_views.product_create, name='product_add'),
    path('products/<int:product_id>/edit/', product_views.product_update, name='product_edit'),
    path('products/<int:product_id>/delete/', product_views.product_delete, name='product_delete'),
    path('orders/', views.orders, name='orders'),
    path('inventory/', views.inventory, name='inventory'),
    path('sales/', views.sales, name='sales')
]