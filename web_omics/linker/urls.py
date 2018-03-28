from django.urls import path

from . import views

urlpatterns = [
    path('', views.LinkerView.as_view(), name='linker_view'),
    path('get_kegg_metabolite_info', views.get_kegg_metabolite_info, name='get_kegg_metabolite_info'),
]