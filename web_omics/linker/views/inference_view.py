from django.shortcuts import render, get_object_or_404
from django import forms
from django_select2.forms import Select2Widget
from django.urls import reverse
from django.contrib import messages
from django.utils import timezone

import pandas as pd

from linker.constants import *
from linker.forms import BaseInferenceForm, T_test_Form, HierarchicalClusteringForm
from linker.models import Analysis, AnalysisData


def inference(request, analysis_id):
    analysis = get_object_or_404(Analysis, pk=analysis_id)
    analysis_data = AnalysisData.objects.filter(analysis=analysis).exclude(inference_type__isnull=True).order_by('timestamp')
    if request.method == 'POST':
        form = BaseInferenceForm(request.POST)
        if form.is_valid():
            data_type = int(form.cleaned_data['data_type'])
            inference_type = int(form.cleaned_data['inference_type'])

            # run t-test analysis
            if inference_type == T_TEST:
                analysis_data = get_analysis_data(analysis, data_type)
                groups = get_groups(analysis_data)
                action_url = reverse('inference_t_test', kwargs={
                    'analysis_id': analysis_id,
                })
                selected_form = T_test_Form()
                selected_form.fields['data_type'].initial = data_type
                selected_form.fields['inference_type'].initial = inference_type
                selected_form.fields['case'] = forms.ChoiceField(choices=groups, widget=Select2Widget())
                selected_form.fields['control'] = forms.ChoiceField(choices=groups, widget=Select2Widget())

            # do hierarchical clustering
            elif inference_type == HIERARCHICAL:
                analysis_data = get_analysis_data(analysis, data_type)
                groups = get_groups(analysis_data) + ((ALL, ALL),)
                action_url = reverse('inference_hierarchical', kwargs={
                    'analysis_id': analysis_id,
                })
                selected_form = HierarchicalClusteringForm()
                selected_form.fields['data_type'].initial = data_type
                selected_form.fields['inference_type'].initial = inference_type
                selected_form.fields['group'] = forms.ChoiceField(choices=groups, widget=Select2Widget())

            else: # default
                action_url = reverse('inference', kwargs={
                    'analysis_id': analysis_id,
                })
                selected_form = BaseInferenceForm(request.POST)

            context = {
                'analysis_id': analysis.pk,
                'analysis_data': analysis_data,
                'form': selected_form,
                'action_url': action_url
            }
            return render(request, 'linker/inference.html', context)
    else:
        action_url = reverse('inference', kwargs={
            'analysis_id': analysis_id,
        })
        base_form = BaseInferenceForm()
        context = {
            'analysis_id': analysis.pk,
            'analysis_data': analysis_data,
            'form': base_form,
            'action_url': action_url
        }
        return render(request, 'linker/inference.html', context)


def inference_t_test(request, analysis_id):
    if request.method == 'POST':

        analysis = get_object_or_404(Analysis, pk=analysis_id)
        form = T_test_Form(request.POST)
        data_type = int(request.POST['data_type'])
        analysis_data = get_analysis_data(analysis, data_type)
        groups = get_groups(analysis_data)
        form.fields['case'] = forms.ChoiceField(choices=groups, widget=Select2Widget())
        form.fields['control'] = forms.ChoiceField(choices=groups, widget=Select2Widget())

        if form.is_valid():
            case = form.cleaned_data['case']
            control = form.cleaned_data['control']
            data_df, design_df = get_dataframes(analysis_data)
            do_t_test(data_df, design_df, case, control)

            # creates a copy of analysis_data
            parent_pk = analysis_data.pk
            analysis_data.pk = None
            analysis_data.parent = get_object_or_404(AnalysisData, pk=parent_pk)
            analysis_data.display_name = 't-test results'
            analysis_data.inference_type = T_TEST
            analysis_data.timestamp = timezone.localtime()
            analysis_data.save()

            messages.success(request, 'Add new inference successful.', extra_tags='primary')
            return inference(request, analysis_id)
        else:
            messages.warning(request, 'Add new inference failed.')

    return inference(request, analysis_id)


def inference_hierarchical(request, analysis_id):
    if request.method == 'POST':

        analysis = get_object_or_404(Analysis, pk=analysis_id)
        form = HierarchicalClusteringForm(request.POST)
        data_type = int(request.POST['data_type'])
        analysis_data = get_analysis_data(analysis, data_type)
        groups = get_groups(analysis_data) + ((ALL, ALL),)
        form.fields['group'] = forms.ChoiceField(choices=groups, widget=Select2Widget())

        if form.is_valid():
            group = form.cleaned_data['group']
            data_df, design_df = get_dataframes(analysis_data)
            do_hierarchical_clustering(data_df, design_df, group)
            messages.success(request, 'Add new inference successful.', extra_tags='primary')
            return inference(request, analysis_id)
        else:
            messages.warning(request, 'Add new inference failed.')

    return inference(request, analysis_id)


def get_analysis_data(analysis, data_type):
    analysis_data = [x for x in analysis.analysisdata_set.all() if x.data_type == data_type][0]
    return analysis_data


def get_dataframes(analysis_data):
    data_df = pd.DataFrame(analysis_data.json_data).set_index('gene_pk')
    design_df = pd.read_json(analysis_data.json_design).set_index('sample')
    return data_df, design_df

def get_groups(analysis_data):
    analysis_groups = set([x.level for x in analysis_data.analysissample_set.all()])
    groups = ((None, NA),) + tuple(zip(analysis_groups, analysis_groups))
    return groups


def do_t_test(data_df, design_df, case, control):
    data_df.to_csv('static/data/debugging/data_df.csv', index=True)
    design_df.to_csv('static/data/debugging/design_df.csv', index=True)


def do_hierarchical_clustering(data_df, design_df, group):
    data_df.to_csv('static/data/debugging/data_df.csv', index=True)
    design_df.to_csv('static/data/debugging/design_df.csv', index=True)
    pass