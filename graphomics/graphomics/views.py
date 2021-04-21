import logging

from django.views.generic.list import ListView
from django.utils import timezone

from django.contrib.auth.decorators import login_required
from django.views.generic import View
from django.utils.decorators import method_decorator

from linker.models import Analysis

logger = logging.getLogger(__name__)

class LoginRequired(View):
    """
    Redirects to login if user is anonymous
    """
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(LoginRequired, self).dispatch(*args, **kwargs)


class ExperimentListView(LoginRequired, ListView):

    model = Analysis
    paginate_by = 100  # if pagination is desired
    template_name = 'graphomics/index.html'

    def get_context_data(self, **kwargs):
        logger.debug('Getting context data')
        context = super().get_context_data(**kwargs)
        context['now'] = timezone.now()
        return context

    def get_queryset(self):
        logger.debug('Getting queryset')
        return Analysis.objects.filter(share__user=self.request.user).order_by('-timestamp')