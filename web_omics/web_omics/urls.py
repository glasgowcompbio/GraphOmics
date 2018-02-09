from django.conf import settings
from django.contrib import admin
from django.urls import include, path
import web_omics.views as views

urlpatterns = [
    path('', views.home),
    path('linker/', include('linker.urls')),
    path('admin/', admin.site.urls),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
