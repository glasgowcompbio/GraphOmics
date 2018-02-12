from django.urls import path

from . import views

urlpatterns = [
    path('', views.LinkerView.as_view(), name='linker_view'),
]