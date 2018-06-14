from django.shortcuts import render, get_object_or_404
from linker.models import Analysis


def settings(request, analysis_id):
    analysis = get_object_or_404(Analysis, pk=analysis_id)
    context = {
        'analysis_id': analysis.pk
    }
    return render(request, 'linker/settings.html', context)