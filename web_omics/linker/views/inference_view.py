from django.shortcuts import render, get_object_or_404
from django import forms
from django_select2.forms import Select2Widget
from django.urls import reverse
from django.contrib import messages
from django.utils import timezone

import numpy as np
import pandas as pd
import jsonpickle

from linker.constants import *
from linker.forms import BaseInferenceForm, T_test_Form, HierarchicalClusteringForm
from linker.models import Analysis, AnalysisData
from linker.views.pipelines import run_deseq, run_ttest


def inference(request, analysis_id):
    analysis = get_object_or_404(Analysis, pk=analysis_id)
    analysis_data_list = AnalysisData.objects.filter(analysis=analysis).exclude(inference_type__isnull=True).order_by('timestamp')
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
                'analysis_data_list': analysis_data_list,
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
            'analysis_data_list': analysis_data_list,
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
            data_df, design_df = get_dataframes(analysis_data, PKS[data_type], SAMPLE_COL)
            to_drop = list(filter(lambda x: x.startswith('padj_') or x.startswith('FC_') or x.startswith('significant_') or x.startswith('obs'), data_df.columns))
            to_drop.append(IDS[data_type])
            data_df = data_df.drop(to_drop, axis=1)

            # drop rows with all NAs and 0s
            data_df = data_df.dropna(how='all')
            data_df = data_df.loc[~(data_df==0).all(axis=1)]

            if data_type == GENOMICS: # run deseq2 here
                pd_df, rld_df, res_ordered = run_deseq(data_df, design_df, 10, case, control)
                result_df = pd_df[['padj', 'log2FoldChange']]
            elif data_type == PROTEOMICS or data_type == METABOLOMICS:
                result_df = run_ttest(data_df, design_df, case, control)

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

            # creates a copy of analysis_data
            parent_pk = analysis_data.pk
            analysis_data.pk = None
            analysis_data.json_data = json_data
            analysis_data.parent = get_object_or_404(AnalysisData, pk=parent_pk)
            analysis_data.inference_type = T_TEST
            analysis_data.timestamp = timezone.localtime()
            if data_type == GENOMICS:
                analysis_data.display_name = 'DeSeq2 %s (case) vs %s (control)' % (case, control)
                analysis_data.metadata = {
                    'rld_df': rld_df.to_json(),
                    'res_ordered': jsonpickle.encode(res_ordered)
                }
            elif data_type == PROTEOMICS or data_type == METABOLOMICS:
                analysis_data.display_name = 't-test %s (case) vs %s (control)' % (case, control)

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
    analysis_data = [x for x in analysis.analysisdata_set.all().order_by('-timestamp') if x.data_type == data_type][0]
    return analysis_data


def get_dataframes(analysis_data, pk_col, sample_col):
    data_df = pd.DataFrame(analysis_data.json_data).set_index(pk_col)
    design_df = pd.read_json(analysis_data.json_design).set_index(sample_col)
    return data_df, design_df


def get_groups(analysis_data):
    if analysis_data.json_design:
        df = pd.read_json(analysis_data.json_design)
        analysis_groups = set(df[GROUP_COL])
        groups = ((None, NA),) + tuple(zip(analysis_groups, analysis_groups))
    else:
        groups = ((None, NA),)
    return groups


def do_hierarchical_clustering(data_df, design_df, group):
    pass