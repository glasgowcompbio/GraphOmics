from django.shortcuts import render, get_object_or_404
from django import forms
from django.views.generic import TemplateView
from django_select2.forms import Select2Widget
from django.urls import reverse
from django.contrib import messages
from django.utils import timezone

import numpy as np
import pandas as pd
import jsonpickle

import plotly.offline as opy
import plotly.graph_objs as go

from linker.forms import BaseInferenceForm
from linker.models import Analysis, AnalysisData
from linker.views.functions import get_last_analysis_data, get_groups, get_dataframes
from linker.views.pipelines import WebOmicsInference
from linker.constants import *


def inference(request, analysis_id):
    analysis = get_object_or_404(Analysis, pk=analysis_id)
    analysis_data_list = AnalysisData.objects.filter(analysis=analysis).exclude(inference_type__isnull=True).order_by(
        'timestamp')
    list_data = get_list_data(analysis_id, analysis_data_list)

    if request.method == 'POST':
        form = BaseInferenceForm(request.POST)
        if form.is_valid():
            data_type = int(form.cleaned_data['data_type'])
            inference_type = int(form.cleaned_data['inference_type'])

            # run t-test analysis
            if inference_type == T_TEST:
                analysis_data = get_last_analysis_data(analysis, data_type)
                groups = get_groups(analysis_data)
                action_url = reverse('inference_deseq_t_test', kwargs={
                    'analysis_id': analysis_id,
                })
                selected_form = BaseInferenceForm()
                selected_form.fields['data_type'].initial = data_type
                selected_form.fields['inference_type'].initial = inference_type
                selected_form.fields['case'] = forms.ChoiceField(choices=groups,
                                                                 widget=Select2Widget(SELECT_WIDGET_ATTRS))
                selected_form.fields['control'] = forms.ChoiceField(choices=groups,
                                                                    widget=Select2Widget(SELECT_WIDGET_ATTRS))

            # do PCA
            elif inference_type == PCA:
                analysis_data = get_last_analysis_data(analysis, data_type)
                groups = get_groups(analysis_data) + ((ALL, ALL),)
                action_url = reverse('inference_pca', kwargs={
                    'analysis_id': analysis_id,
                })
                selected_form = BaseInferenceForm()
                selected_form.fields['data_type'].initial = data_type
                selected_form.fields['inference_type'].initial = inference_type
                selected_form.fields['group'] = forms.ChoiceField(choices=groups,
                                                                  widget=Select2Widget(SELECT_WIDGET_ATTRS))

            else:  # default
                action_url = reverse('inference', kwargs={
                    'analysis_id': analysis_id,
                })
                selected_form = BaseInferenceForm(request.POST)

            context = {
                'analysis_id': analysis.pk,
                'list_data': list_data,
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
            'list_data': list_data,
            'form': base_form,
            'action_url': action_url
        }
        return render(request, 'linker/inference.html', context)


def get_list_data(analysis_id, analysis_data_list):
    list_data = []
    for analysis_data in analysis_data_list:
        inference_type = analysis_data.inference_type

        # when clicked, go to the Explore Data page
        click_url = None
        if inference_type == T_TEST or inference_type == REACTOME:
            click_url = reverse('explore_data', kwargs={
                'analysis_id': analysis_id,
            })

        # when clicked, show the Explore Analysis Data page
        elif inference_type == PCA:
            click_url = reverse('pca_result', kwargs={
                'analysis_id': analysis_id,
                'analysis_data_id': analysis_data.id
            })

        item = [analysis_data, click_url]
        list_data.append(item)
    return list_data


def inference_deseq_t_test(request, analysis_id):
    if request.method == 'POST':

        analysis = get_object_or_404(Analysis, pk=analysis_id)
        form = BaseInferenceForm(request.POST)
        data_type = int(request.POST['data_type'])
        analysis_data = get_last_analysis_data(analysis, data_type)
        groups = get_groups(analysis_data)
        form.fields['case'] = forms.ChoiceField(choices=groups, widget=Select2Widget())
        form.fields['control'] = forms.ChoiceField(choices=groups, widget=Select2Widget())

        if form.is_valid():
            case = form.cleaned_data['case']
            control = form.cleaned_data['control']
            data_df, design_df = get_dataframes(analysis_data, PKS[data_type], SAMPLE_COL)

            if data_type == GENOMICS:  # run deseq2 here
                wi = WebOmicsInference(data_df, design_df, data_type)
                pd_df, rld_df, res_ordered = wi.run_deseq(10, case, control)
                result_df = pd_df[['padj', 'log2FoldChange']]
            elif data_type == PROTEOMICS or data_type == METABOLOMICS:
                wi = WebOmicsInference(data_df, design_df, data_type, min_value=5000)
                result_df = wi.run_ttest(case, control)

            res = result_df.to_dict()
            json_data = analysis_data.json_data
            label = '%s_vs_%s' % (case, control)
            for i in range(len(json_data)):
                item = json_data[i]
                key = item[PKS[data_type]]
                try:
                    padj = res['padj'][key]
                    if np.isnan(padj):
                        padj = None
                except KeyError:
                    padj = None
                try:
                    lfc = res['log2FoldChange'][key]
                    if np.isnan(lfc) or np.isinf(lfc):
                        lfc = None
                except KeyError:
                    lfc = None
                item['padj_%s' % label] = padj
                item['FC_%s' % label] = lfc

                # check if item is statistically significant
                padj_values = np.array([item[k] for k in item.keys() if 'padj' in k and item[k] is not None])
                check = (padj_values > 0) & (padj_values < T_TEST_THRESHOLD)
                if len(check) == 0:
                    item['significant_all'] = False
                    item['significant_any'] = False
                else:
                    item['significant_all'] = np.all(check)
                    item['significant_any'] = np.any(check)

            # create a new analysis data
            if data_type == GENOMICS:
                display_name = 'DESeq2: %s (case) vs %s (control)' % (case, control)
                metadata = {
                    'rld_df': rld_df.to_json(),
                    'res_ordered': jsonpickle.encode(res_ordered)
                }
            elif data_type == PROTEOMICS or data_type == METABOLOMICS:
                display_name = 't-test: %s (case) vs %s (control)' % (case, control)
                metadata = {}
            copy_analysis_data(analysis_data, json_data, display_name, metadata, T-TEST)

            messages.success(request, 'Add new inference successful.', extra_tags='primary')
            return inference(request, analysis_id)
        else:
            messages.warning(request, 'Add new inference failed.')

    return inference(request, analysis_id)


def copy_analysis_data(analysis_data, new_json_data, new_display_name, new_metadata, inference_type):
    parent_pk = analysis_data.pk
    # creates a copy of analysis_data by setting the pk to None
    analysis_data.pk = None
    analysis_data.json_data = new_json_data
    analysis_data.parent = get_object_or_404(AnalysisData, pk=parent_pk)
    analysis_data.inference_type = inference_type
    analysis_data.timestamp = timezone.localtime()
    analysis_data.display_name = new_display_name
    analysis_data.metadata.update(new_metadata)
    analysis_data.save()
    return analysis_data


def inference_pca(request, analysis_id):
    if request.method == 'POST':

        analysis = get_object_or_404(Analysis, pk=analysis_id)
        form = BaseInferenceForm(request.POST)
        data_type = int(request.POST['data_type'])
        analysis_data = get_last_analysis_data(analysis, data_type)
        groups = get_groups(analysis_data) + ((ALL, ALL),)
        form.fields['group'] = forms.ChoiceField(choices=groups, widget=Select2Widget())

        if form.is_valid():
            group = form.cleaned_data['group']
            index_col = IDS[data_type]
            data_df, design_df = get_dataframes(analysis_data, index_col, SAMPLE_COL)
            do_pca(data_df, design_df, group)
            display_name = 'PCA: %s' % group
            metadata = {
                'pca_group': group
            }
            copy_analysis_data(analysis_data, analysis_data.json_data, display_name, metadata, PCA)
            messages.success(request, 'Add new inference successful.', extra_tags='primary')
            return inference(request, analysis_id)
        else:
            messages.warning(request, 'Add new inference failed.')

    return inference(request, analysis_id)


def do_pca(data_df, design_df, group):
    pass


class PCAResult(TemplateView):
    template_name = 'linker/inference_pca.html'

    def get_context_data(self, **kwargs):
        analysis_id = self.kwargs['analysis_id']
        analysis_data_id = self.kwargs['analysis_data_id']
        analysis_data = AnalysisData.objects.get(pk=analysis_data_id)
        pca_group = analysis_data.metadata['pca_group']

        x = [-2, 0, 4, 6, 7]
        y = [q ** 2 - q + 3 for q in x]
        trace1 = go.Scatter(x=x, y=y, marker={'color': 'red', 'symbol': 104, 'size': 10},
                            mode="lines", name='1st Trace')

        data = go.Data([trace1])
        layout = go.Layout(title="Meine Daten", xaxis={'title': 'x1'}, yaxis={'title': 'x2'})
        figure = go.Figure(data=data, layout=layout)
        div = opy.plot(figure, auto_open=False, output_type='div')

        context = super(PCAResult, self).get_context_data(**kwargs)
        context.update({
            'graph': div,
            'analysis_id': analysis_id,
            'pca_group': pca_group,
        })
        return context
