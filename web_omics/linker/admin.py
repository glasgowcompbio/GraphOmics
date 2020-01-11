from django.contrib import admin

from .models import *

admin.site.register(Analysis)
admin.site.register(AnalysisData)
admin.site.register(AnalysisAnnotation)
admin.site.register(AnalysisGroup)