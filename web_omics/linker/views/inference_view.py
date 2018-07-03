from django.shortcuts import render, get_object_or_404
from django import forms
from django_select2.forms import Select2Widget
from django.urls import reverse
from django.contrib import messages

from linker.constants import *
from linker.forms import BaseInferenceForm, T_test_Form
from linker.models import Analysis


def inference(request, analysis_id):
    if request.method == 'POST':
        analysis = get_object_or_404(Analysis, pk=analysis_id)
        form = BaseInferenceForm(request.POST)
        if form.is_valid():
            data_type = int(form.cleaned_data['data_type'])
            inference_type = int(form.cleaned_data['inference_type'])

            if inference_type == T_TEST:
                groups = get_groups(analysis, data_type)
                action_url = reverse('inference_t_test', kwargs={
                    'analysis_id': analysis_id,
                })
                selected_form = T_test_Form()
                selected_form.fields['data_type'].initial = data_type
                selected_form.fields['inference_type'].initial = inference_type
                selected_form.fields['case'] = forms.ChoiceField(choices=groups, widget=Select2Widget())
                selected_form.fields['control'] = forms.ChoiceField(choices=groups, widget=Select2Widget())

            else: # default
                action_url = reverse('inference', kwargs={
                    'analysis_id': analysis_id,
                })
                selected_form = BaseInferenceForm(request.POST)

            context = {
                'analysis_id': analysis.pk,
                'form': selected_form,
                'action_url': action_url
            }
            return render(request, 'linker/inference.html', context)
    else:
        analysis = get_object_or_404(Analysis, pk=analysis_id)
        action_url = reverse('inference', kwargs={
            'analysis_id': analysis_id,
        })
        base_form = BaseInferenceForm()
        context = {
            'analysis_id': analysis.pk,
            'form': base_form,
            'action_url': action_url
        }
        return render(request, 'linker/inference.html', context)


def inference_t_test(request, analysis_id):
    if request.method == 'POST':

        analysis = get_object_or_404(Analysis, pk=analysis_id)
        form = T_test_Form(request.POST)
        data_type = int(request.POST['data_type'])
        groups = get_groups(analysis, data_type)
        form.fields['case'] = forms.ChoiceField(choices=groups, widget=Select2Widget())
        form.fields['control'] = forms.ChoiceField(choices=groups, widget=Select2Widget())

        if form.is_valid():
            case = form.cleaned_data['case']
            control = form.cleaned_data['control']
            do_t_test(analysis, case, control)
            messages.success(request, 'Add new inference successful.', extra_tags='primary')
            return inference(request, analysis_id)
        else:
            messages.warning(request, 'Add new inference failed.')

    return inference(request, analysis_id)


def get_groups(analysis, data_type):
    analysis_data = [x for x in analysis.analysisdata_set.all() if x.data_type == data_type][0]
    analysis_groups = set([x.group_name for x in analysis_data.analysissample_set.all()])
    groups = ((None, NA),) + tuple(zip(range(len(analysis_groups)), analysis_groups))
    return groups


def do_t_test(analysis, case, control):
    pass