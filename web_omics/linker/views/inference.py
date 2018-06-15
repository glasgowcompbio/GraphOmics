from django.shortcuts import render, get_object_or_404
from linker.models import Analysis


def inference(request, analysis_id):
    analysis = get_object_or_404(Analysis, pk=analysis_id)
    context = {
        'analysis_id': analysis.pk
    }
    return render(request, 'linker/inference.html', context)