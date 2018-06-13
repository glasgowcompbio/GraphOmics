from django.shortcuts import render
from django.template.loader import render_to_string
from django.views.generic.list import ListView
from django.utils import timezone

from linker.models import Analysis


class ExperimentListView(ListView):

    model = Analysis
    paginate_by = 100  # if pagination is desired
    template_name = 'webOmics/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['now'] = timezone.now()
        return context
