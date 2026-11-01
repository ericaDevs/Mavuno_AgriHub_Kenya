from . import views
from django.urls import path

app_name = 'authentication'

urlpatterns = [
    path('register/', views.register, name = 'register'),
    path('login/', views.login, name='login'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('logout/', views.logout, name='logout'),
]