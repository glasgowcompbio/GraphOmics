import django.contrib.auth.views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('profile/', views.ProfileUpdate.as_view(), name='profile'),
    path('change_password/', auth_views.PasswordChangeView.as_view(success_url='profile'), name='password_change')
]