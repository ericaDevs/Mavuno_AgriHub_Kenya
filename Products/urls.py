from . import views
from django.urls import path

app_name = 'products'

urlpatterns = [
    path('', views.catalog, name='products'),
    path('cart/', views.cart_page, name='cart'),
    path('cart/add/<int:pk>/', views.cart_add, name='cart_add'),
    path('cart/update/<int:pk>/', views.cart_update, name='cart_update'),
    path('cart/remove/<int:pk>/', views.cart_remove, name='cart_remove'),
    path('<int:pk>/', views.product_detail, name='detail'),
]