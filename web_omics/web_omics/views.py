from django.shortcuts import render
from django.template.loader import render_to_string


def home(request):
    context_dict = {}
    return render(request,'webOmics/index.html',context_dict)