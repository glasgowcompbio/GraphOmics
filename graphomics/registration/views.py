import logging
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse, reverse_lazy
from django.views.generic.edit import UpdateView
from django.contrib import messages

from linker.models import Analysis
from registration.forms import UserForm

User = get_user_model()
logger = logging.getLogger(__name__)

def user_logout(request):
    logout(request)
    return HttpResponseRedirect('/')


def register(request):
    registered = False
    if request.method == 'POST':
        user_form = UserForm(data=request.POST)
        if user_form.is_valid():
            user = user_form.save()
            user.set_password(user.password)
            user.save()
            registered = True

        else:
            logger.debug(user_form.errors)
    else:
        user_form = UserForm()

    context_dict = {'user_form': user_form, 'registered': registered}
    return render(request,
                  'registration/register.html', context_dict)


def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(username=username, password=password)
        if user:
            if user.is_active:
                login(request, user)
                return HttpResponseRedirect(reverse('experiment_list_view'))
            else:
                error_message = "Account {0} has been disabled".format(username)
                messages.warning(request, error_message)
                return render(request, 'registration/login.html', {})
        else:
            if username == 'guest': # auto-create if not there
                guest_user = User.objects.create_user(username='guest', password='guest')
                login(request, guest_user)
                return HttpResponseRedirect(reverse('experiment_list_view'))
            else:
                error_message = "Invalid login details for {0}".format(username)
                messages.warning(request, error_message)
                return render(request, 'registration/login.html', {})

    else: # GET
        object_list = Analysis.objects.filter(public=True).order_by('-timestamp')
        return render(request, 'registration/login.html', {
            'object_list': object_list
        })


class ProfileUpdate(UpdateView):
    model = User
    template_name = 'registration/user_update.html'
    success_url = reverse_lazy('experiment_list_view')
    fields = ['first_name', 'last_name', 'email']

    def get_object(self, queryset=None):
        return self.request.user