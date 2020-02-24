from django.conf import settings
from django.contrib import admin
from django.urls import include, path
import web_omics.views as views

urlpatterns = [
    path('', views.ExperimentListView.as_view(), name='experiment_list_view'),
    path('linker/', include('linker.urls')),
    path('grappelli/', include('grappelli.urls')),  # grappelli URLS
    path('admin/', admin.site.urls),
    path('registration/', include('registration.urls')),
]