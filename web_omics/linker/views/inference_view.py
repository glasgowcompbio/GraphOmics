import json
from urllib.parse import quote

import jsonpickle
import numpy as np
import pandas as pd
import requests
from django import forms
from django.contrib import messages
from django.forms import TextInput, DecimalField
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.generic import TemplateView
from django_select2.forms import Select2Widget
from loguru import logger
from pals.common import PLAGE_WEIGHT, HG_WEIGHT
from sklearn import preprocessing
from sklearn.decomposition import PCA as skPCA

from linker.constants import *
from linker.forms import BaseInferenceForm
from linker.models import Analysis, AnalysisData
from linker.views.functions import get_last_analysis_data, get_groups, get_dataframes, get_standardized_df, \
    get_group_members, fig_to_div
from linker.views.pathway_analysis import get_pals_data_source, run_pals, update_pathway_analysis_data, run_ora, \
    run_gsea
from linker.views.pipelines import WebOmicsInference


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
            if inference_type == INFERENCE_T_TEST:
                analysis_data = get_last_analysis_data(analysis, data_type)
                groups = get_groups(analysis_data)
                action_url = reverse('inference_t_test', kwargs={
                    'analysis_id': analysis_id,
                })
                selected_form = get_case_control_form(data_type, groups, inference_type)

            elif inference_type == INFERENCE_DESEQ:
                analysis_data = get_last_analysis_data(analysis, data_type)
                groups = get_groups(analysis_data)
                action_url = reverse('inference_deseq', kwargs={
                    'analysis_id': analysis_id,
                })
                selected_form = get_case_control_form(data_type, groups, inference_type)

            elif inference_type == INFERENCE_LIMMA:
                analysis_data = get_last_analysis_data(analysis, data_type)
                groups = get_groups(analysis_data)
                action_url = reverse('inference_limma', kwargs={
                    'analysis_id': analysis_id,
                })
                selected_form = get_case_control_form(data_type, groups, inference_type)

            # do PCA
            elif inference_type == INFERENCE_PCA:
                analysis_data = get_last_analysis_data(analysis, data_type)
                action_url = reverse('inference_pca', kwargs={
                    'analysis_id': analysis_id,
                })
                selected_form = BaseInferenceForm()
                selected_form.fields['data_type'].initial = data_type
                selected_form.fields['inference_type'].initial = inference_type
                choices = zip(range(2, 11), range(2, 11))
                selected_form.fields['pca_n_components'] = forms.ChoiceField(choices=choices,
                                                                             widget=Select2Widget(SELECT_WIDGET_ATTRS),
                                                                             label='PCA components')

            # do PALS
            elif inference_type == INFERENCE_PALS:
                analysis_data = get_last_analysis_data(analysis, data_type)
                groups = get_groups(analysis_data)
                action_url = reverse('inference_pals', kwargs={
                    'analysis_id': analysis_id,
                })
                selected_form = get_case_control_form(data_type, groups, inference_type)
                selected_form.fields['plage_weight'] = forms.IntegerField(min_value=0, initial=PLAGE_WEIGHT,
                                                                          label='Intensity weight')
                selected_form.fields['hg_weight'] = forms.IntegerField(min_value=0, initial=HG_WEIGHT,
                                                                       label='Coverage weight')

            # do ORA
            elif inference_type == INFERENCE_ORA:
                analysis_data = get_last_analysis_data(analysis, data_type)
                groups = get_groups(analysis_data)
                action_url = reverse('inference_ora', kwargs={
                    'analysis_id': analysis_id,
                })
                selected_form = get_case_control_form(data_type, groups, inference_type)

            # do GSEA
            elif inference_type == INFERENCE_GSEA:
                analysis_data = get_last_analysis_data(analysis, data_type)
                groups = get_groups(analysis_data)
                action_url = reverse('inference_gsea', kwargs={
                    'analysis_id': analysis_id,
                })
                selected_form = get_case_control_form(data_type, groups, inference_type)

            # do Reactome Analysis Service
            elif inference_type == INFERENCE_REACTOME:
                selected_form = BaseInferenceForm()
                selected_form.fields['data_type'].initial = data_type
                selected_form.fields['inference_type'].initial = inference_type

                if data_type == MULTI_OMICS:
                    for dtype in [GENOMICS, PROTEOMICS, METABOLOMICS]:
                        analysis_data = get_last_analysis_data(analysis, dtype)
                        populate_reactome_choices(analysis_data, dtype, selected_form)
                else:
                    analysis_data = get_last_analysis_data(analysis, data_type)
                    populate_reactome_choices(analysis_data, data_type, selected_form)

                selected_form.fields['threshold'] = DecimalField(required=True, widget=TextInput(
                    attrs={'autocomplete': 'off', 'type': 'number', 'min': '0', 'max': '1', 'step': '0.05',
                           'size': '10'}))
                selected_form.fields['threshold'].initial = 0.0

                action_url = reverse('inference_reactome', kwargs={
                    'analysis_id': analysis_id,
                })

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


def populate_reactome_choices(analysis_data, data_type, selected_form):
    data_df, design_df = get_dataframes(analysis_data, PKS)
    if design_df is not None:
        comparisons = [col for col in data_df.columns if col.startswith(FC_COL_PREFIX)]
        comparisons = list(map(lambda comp: comp.replace(FC_COL_PREFIX, ''), comparisons))
        comparison_choices = ((None, NA),) + tuple(zip(comparisons, comparisons))
        data_type_comp_fieldname = '%s_comparison' % AddNewDataDict[data_type]
        selected_form.fields[data_type_comp_fieldname] = forms.ChoiceField(required=False, choices=comparison_choices,
                                                                           widget=Select2Widget(SELECT_WIDGET_ATTRS))
        return data_df, data_type_comp_fieldname
    else:
        return None, None


def get_case_control_form(data_type, groups, inference_type):
    selected_form = BaseInferenceForm()
    selected_form.fields['data_type'].initial = data_type
    selected_form.fields['inference_type'].initial = inference_type
    selected_form.fields['case'] = forms.ChoiceField(choices=groups,
                                                     widget=Select2Widget(SELECT_WIDGET_ATTRS))
    selected_form.fields['control'] = forms.ChoiceField(choices=groups,
                                                        widget=Select2Widget(SELECT_WIDGET_ATTRS))
    return selected_form


def get_list_data(analysis_id, analysis_data_list):
    list_data = []
    for analysis_data in analysis_data_list:
        inference_type = analysis_data.inference_type

        # when clicked, go to the Explore Data page
        click_url = None
        if inference_type == INFERENCE_T_TEST or \
                inference_type == INFERENCE_DESEQ or \
                inference_type == INFERENCE_LIMMA or \
                inference_type == INFERENCE_PALS or \
                inference_type == INFERENCE_ORA or \
                inference_type == INFERENCE_GSEA:
            click_url = reverse('explore_data', kwargs={
                'analysis_id': analysis_id,
            })

        # when clicked, show the Explore Analysis Data page
        elif inference_type == INFERENCE_PCA:
            click_url = reverse('pca_result', kwargs={
                'analysis_id': analysis_id,
                'analysis_data_id': analysis_data.id
            })

        # when clicked, go to Reactome
        elif inference_type == INFERENCE_REACTOME:
            if 'reactome_url' in analysis_data.metadata:
                click_url = analysis_data.metadata['reactome_url']

        item = [analysis_data, click_url]
        list_data.append(item)
    return list_data


def inference_t_test(request, analysis_id):
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
            data_df, design_df = get_dataframes(analysis_data, PKS)

            if data_type == GENOMICS:
                min_replace = MIN_REPLACE_GENOMICS
            elif data_type == PROTEOMICS or data_type == METABOLOMICS:
                min_replace = MIN_REPLACE_PROTEOMICS_METABOLOMICS
            wi = WebOmicsInference(data_df, design_df, data_type, min_value=min_replace)
            result_df = wi.run_ttest(case, control)
            json_data = get_updated_json_data(analysis_data, data_type, case, control, result_df)

            # create a new analysis data
            display_name = 't-test: %s_vs_%s' % (case, control)
            metadata = None
            data_type = analysis_data.data_type
            copy_analysis_data(analysis_data, json_data, display_name, metadata, data_type, INFERENCE_T_TEST)
            messages.success(request, 'Add new inference successful.', extra_tags='primary')
            return inference(request, analysis_id)
        else:
            messages.warning(request, 'Add new inference failed.')

    return inference(request, analysis_id)


def inference_deseq(request, analysis_id):
    if request.method == 'POST':
        data_type = int(request.POST['data_type'])
        if data_type == PROTEOMICS or data_type == METABOLOMICS:
            messages.warning(request, 'Add new inference failed. DESeq2 only works for discrete count data.')
            return inference(request, analysis_id)

        analysis = get_object_or_404(Analysis, pk=analysis_id)
        form = BaseInferenceForm(request.POST)
        analysis_data = get_last_analysis_data(analysis, data_type)
        groups = get_groups(analysis_data)
        form.fields['case'] = forms.ChoiceField(choices=groups, widget=Select2Widget())
        form.fields['control'] = forms.ChoiceField(choices=groups, widget=Select2Widget())

        if form.is_valid():
            case = form.cleaned_data['case']
            control = form.cleaned_data['control']
            data_df, design_df = get_dataframes(analysis_data, PKS)

            # run deseq2 here
            wi = WebOmicsInference(data_df, design_df, data_type)
            try:
                pd_df, rld_df, res_ordered = wi.run_deseq(MIN_REPLACE_GENOMICS, case, control)
            except Exception as e:
                logger.warning('Failed to run DESeq2: %s' % str(e))
                messages.warning(request, 'Add new inference failed.')
                return inference(request, analysis_id)
            result_df = pd_df[['padj', 'log2FoldChange']]
            json_data = get_updated_json_data(analysis_data, data_type, case, control, result_df)

            # create a new analysis data
            display_name = 'DESeq2: %s_vs_%s' % (case, control)
            metadata = {
                'rld_df': rld_df.to_json(),
                'res_ordered': jsonpickle.encode(res_ordered)
            }
            data_type = analysis_data.data_type
            copy_analysis_data(analysis_data, json_data, display_name, metadata, data_type, INFERENCE_DESEQ)
            messages.success(request, 'Add new inference successful.', extra_tags='primary')
            return inference(request, analysis_id)
        else:
            messages.warning(request, 'Add new inference failed.')

    return inference(request, analysis_id)


def inference_limma(request, analysis_id):
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
            data_df, design_df = get_dataframes(analysis_data, PKS)

            if data_type == GENOMICS:
                min_replace = MIN_REPLACE_GENOMICS
            elif data_type == PROTEOMICS or data_type == METABOLOMICS:
                min_replace = MIN_REPLACE_PROTEOMICS_METABOLOMICS
            wi = WebOmicsInference(data_df, design_df, data_type, min_value=min_replace)
            result_df = wi.run_limma(case, control)
            json_data = get_updated_json_data(analysis_data, data_type, case, control, result_df)

            # create a new analysis data
            display_name = 'limma: %s_vs_%s' % (case, control)
            metadata = None
            data_type = analysis_data.data_type
            copy_analysis_data(analysis_data, json_data, display_name, metadata, data_type, INFERENCE_LIMMA)
            messages.success(request, 'Add new inference successful.', extra_tags='primary')
            return inference(request, analysis_id)
        else:
            messages.warning(request, 'Add new inference failed.')

    return inference(request, analysis_id)


def get_updated_json_data(analysis_data, data_type, case, control, result_df):
    res = result_df.to_dict()
    json_data = analysis_data.json_data
    label = '%s_vs_%s' % (case, control)
    padj_label = 'padj_%s' % label
    fc_label = 'FC_%s' % label

    #  remove the previous DE result if exists
    for i in range(len(json_data)):
        item = json_data[i]
        if padj_label in item:
            del item[padj_label]
            logger.debug('Removed old padj value')
        if fc_label in item:
            del item[fc_label]
            logger.debug('Removed old FC value')

    # set new DE result to json_data
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
        item[padj_label] = padj
        item[fc_label] = lfc
    return json_data


def copy_analysis_data(analysis_data, new_json_data, new_display_name, new_metadata, new_data_type, inference_type):
    parent_pk = analysis_data.pk
    # creates a copy of analysis_data by setting the pk to None
    analysis_data.pk = None
    analysis_data.json_data = new_json_data
    analysis_data.parent = get_object_or_404(AnalysisData, pk=parent_pk)
    analysis_data.inference_type = inference_type
    analysis_data.timestamp = timezone.localtime()
    analysis_data.display_name = new_display_name
    analysis_data.data_type = new_data_type
    if analysis_data.metadata is not None and new_metadata is not None:
        analysis_data.metadata.update(new_metadata)
    analysis_data.save()


def inference_pca(request, analysis_id):
    if request.method == 'POST':

        analysis = get_object_or_404(Analysis, pk=analysis_id)
        form = BaseInferenceForm(request.POST)
        data_type = int(request.POST['data_type'])
        analysis_data = get_last_analysis_data(analysis, data_type)
        choices = zip(range(2, 11), range(2, 11))
        form.fields['pca_n_components'] = forms.ChoiceField(choices=choices,
                                                            widget=Select2Widget(SELECT_WIDGET_ATTRS),
                                                            label='PCA Components')

        if form.is_valid():
            n_components = int(form.cleaned_data['pca_n_components'])

            # do pca on the samples
            X_proj, X_std, pca = get_pca_proj(analysis_data, n_components)
            if pca is not None:
                var_exp = pca.explained_variance_ratio_

                # store pca results to the metadata field of this AnalysisData
                metadata = {
                    'pca_n_components': jsonpickle.dumps(n_components),
                    'pca_X_std_index': jsonpickle.dumps(X_std.index.values),
                    'pca_X_proj': jsonpickle.dumps(X_proj),
                    'pca_var_exp': jsonpickle.dumps(var_exp)
                }
                display_name = 'PCA: %s components' % n_components
                data_type = analysis_data.data_type
                copy_analysis_data(analysis_data, analysis_data.json_data, display_name, metadata, data_type,
                                   INFERENCE_PCA)
                messages.success(request, 'Add new inference successful.', extra_tags='primary')
            else:
                messages.warning(request, 'Add new inference failed. No data found.')

            return inference(request, analysis_id)
        else:
            messages.warning(request, 'Add new inference failed.')

    return inference(request, analysis_id)


def get_pca_proj(analysis_data, n_components):
    axis = 0
    X_std, data_df, design_df = get_standardized_df(analysis_data, axis, pk_cols=PKS)

    if design_df is not None:
        X_std = X_std.transpose()
        pca = skPCA(n_components)
        X_proj = pca.fit_transform(X_std)
    else:
        X_std = None
        X_proj = None
        pca = None

    return X_proj, X_std, pca


class PCAResult(TemplateView):
    template_name = 'linker/inference_pca.html'

    def get_context_data(self, **kwargs):
        analysis_id = self.kwargs['analysis_id']
        analysis_data_id = self.kwargs['analysis_data_id']
        analysis_data = AnalysisData.objects.get(pk=analysis_data_id)

        n_components = jsonpickle.loads(analysis_data.metadata['pca_n_components'])
        X_std_index = jsonpickle.loads(analysis_data.metadata['pca_X_std_index'])
        X_proj = jsonpickle.loads(analysis_data.metadata['pca_X_proj'])
        var_exp = jsonpickle.loads(analysis_data.metadata['pca_var_exp'])

        # make pca plot
        fig = self.get_pca_plot(analysis_data, X_std_index, X_proj)
        pca_plot = fig_to_div(fig)

        # make explained variance plot
        fig = self.get_variance_plot(var_exp)
        variance_plot = fig_to_div(fig)

        # set the div to context
        context = super(PCAResult, self).get_context_data(**kwargs)
        context.update({
            'pca_plot': pca_plot,
            'variance_plot': variance_plot,
            'analysis_id': analysis_id,
            'n_components': n_components,
        })
        return context

    def get_variance_plot(self, var_exp):
        cum_var_exp = np.cumsum(var_exp)
        trace1 = dict(
            type='bar',
            x=['PC %s' % (i + 1) for i in range(len(var_exp))],
            y=var_exp,
            name='Individual'
        )
        trace2 = dict(
            type='scatter',
            x=['PC %s' % (i + 1) for i in range(len(var_exp))],
            y=cum_var_exp,
            name='Cumulative'
        )
        data = [trace1, trace2]
        layout = dict(
            title='Explained variance by different principal components',
            yaxis=dict(
                title='Explained variance'
            ),
            width=800,
            annotations=list([
                dict(
                    x=1.20,
                    y=1.05,
                    xref='paper',
                    yref='paper',
                    text='Explained Variance',
                    showarrow=False,
                )
            ])
        )
        fig = dict(data=data, layout=layout)
        return fig

    def get_pca_plot(self, analysis_data, X_std_index, X_proj):
        data = []
        group_members = get_group_members(analysis_data)
        for group in group_members:
            members = group_members[group]
            pos = np.in1d(X_std_index, members).nonzero()[0]  # find position of group members in sample indices of X
            labels = X_std_index[pos]
            trace = dict(
                type='scatter',
                x=X_proj[pos, 0],
                y=X_proj[pos, 1],
                mode='markers',
                name=group,
                text=labels,
                marker=dict(
                    size=12,
                    line=dict(
                        color='rgba(217, 217, 217, 0.14)',
                        width=0.5),
                    opacity=0.8)
            )
            data.append(trace)
        layout = dict(
            width=800,
            title='PCA Projection',
            xaxis=dict(title='PC1', showline=False),
            yaxis=dict(title='PC2', showline=False)
        )
        fig = dict(data=data, layout=layout)
        return fig


def inference_pals(request, analysis_id):
    if request.method == 'POST':

        analysis = get_object_or_404(Analysis, pk=analysis_id)
        form = BaseInferenceForm(request.POST)
        data_type = int(request.POST['data_type'])
        analysis_data = get_last_analysis_data(analysis, data_type)
        groups = get_groups(analysis_data)
        form.fields['case'] = forms.ChoiceField(choices=groups, widget=Select2Widget())
        form.fields['control'] = forms.ChoiceField(choices=groups, widget=Select2Widget())
        form.fields['plage_weight'] = forms.IntegerField(min_value=0, initial=PLAGE_WEIGHT, label='Measurement weight')
        form.fields['hg_weight'] = forms.IntegerField(min_value=0, initial=HG_WEIGHT, label='Coverage weight')

        if form.is_valid():
            case = form.cleaned_data['case']
            control = form.cleaned_data['control']
            plage_weight = form.cleaned_data['plage_weight']
            hg_weight = form.cleaned_data['hg_weight']

            # get pals data source from the current analysis_data
            pals_data_source = get_pals_data_source(analysis, analysis_data, case, control)
            if pals_data_source is None:
                messages.warning(request, 'Add new inference failed. No data found.')
                return inference(request, analysis_id)

            # run pals
            pals_df = run_pals(pals_data_source, plage_weight, hg_weight)

            # check for NaN in the results. It shouldn't happen.
            if pals_df.isnull().values.any():
                logger.warning('PALS result contains NaN! These rows will be deleted.')
                logger.warning(pals_df[pals_df.isnull().any(axis=1)])
                pals_df = pals_df.dropna()

            # update PALS results to database
            pathway_analysis_data = get_last_analysis_data(analysis, PATHWAYS)
            new_json_data = update_pathway_analysis_data(pathway_analysis_data, pals_df)
            new_display_name = 'PLAGE %s (%d:%d): %s_vs_%s' % (pals_data_source.database_name,
                                                               plage_weight, hg_weight,
                                                               case, control)
            data_type = pathway_analysis_data.data_type
            copy_analysis_data(pathway_analysis_data, new_json_data, new_display_name, None, data_type,
                               INFERENCE_PALS)
            messages.success(request, 'Add new inference successful.', extra_tags='primary')
            return inference(request, analysis_id)

        else:
            messages.warning(request, 'Add new inference failed.')

    return inference(request, analysis_id)


def inference_ora(request, analysis_id):
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

            # get pals data source from the current analysis_data
            pals_data_source = get_pals_data_source(analysis, analysis_data, case, control)
            if pals_data_source is None:
                messages.warning(request, 'Add new inference failed. No data found.')
                return inference(request, analysis_id)

            # run ora
            pals_df = run_ora(pals_data_source)
            # update ORA results to database
            pathway_analysis_data = get_last_analysis_data(analysis, PATHWAYS)
            new_json_data = update_pathway_analysis_data(pathway_analysis_data, pals_df)
            new_display_name = 'ORA %s: %s_vs_%s' % (pals_data_source.database_name,
                                                     case, control)
            data_type = pathway_analysis_data.data_type
            copy_analysis_data(pathway_analysis_data, new_json_data, new_display_name, None, data_type,
                               INFERENCE_ORA)
            messages.success(request, 'Add new inference successful.', extra_tags='primary')
            return inference(request, analysis_id)

        else:
            messages.warning(request, 'Add new inference failed.')

    return inference(request, analysis_id)


def inference_gsea(request, analysis_id):
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

            # get pals data source from the current analysis_data
            pals_data_source = get_pals_data_source(analysis, analysis_data, case, control)
            if pals_data_source is None:
                messages.warning(request, 'Add new inference failed. No data found.')
                return inference(request, analysis_id)

            # run ora
            pals_df = run_gsea(pals_data_source)
            # update ORA results to database
            pathway_analysis_data = get_last_analysis_data(analysis, PATHWAYS)
            new_json_data = update_pathway_analysis_data(pathway_analysis_data, pals_df)
            new_display_name = 'GSEA %s: %s_vs_%s' % (pals_data_source.database_name,
                                                      case, control)
            data_type = pathway_analysis_data.data_type
            copy_analysis_data(pathway_analysis_data, new_json_data, new_display_name, None, data_type,
                               INFERENCE_GSEA)
            messages.success(request, 'Add new inference successful.', extra_tags='primary')
            return inference(request, analysis_id)

        else:
            messages.warning(request, 'Add new inference failed.')

    return inference(request, analysis_id)


# TODO: refactor task
# rename BaseInferenceForm.data_type to source_data
# remove data type genomics, use transcriptomics

def inference_reactome(request, analysis_id):
    if request.method == 'POST':
        analysis = get_object_or_404(Analysis, pk=analysis_id)
        form = BaseInferenceForm(request.POST)
        data_type = int(request.POST['data_type'])

        data_types = [data_type]
        if data_type == MULTI_OMICS:
            data_types = [GENOMICS, PROTEOMICS, METABOLOMICS]

        omics_data = {}
        for dtype in data_types:
            analysis_data = get_last_analysis_data(analysis, dtype)
            data_df, data_type_comp_fieldname = populate_reactome_choices(analysis_data, dtype, form)
            if data_df is not None:
                # https://reactome.org/userguide/analysis
                # Identifiers that contain only numbers such as those from OMIM and EntrezGene must be prefixed by the
                # source database name and a colon e.g. MIM:602544, EntrezGene:55718. Mixed identifier lists
                # (different protein identifiers or protein/gene identifiers) may be used.
                # Identifiers must be one per line.

                # database_name, _ = _get_database_name(analysis, analysis_data)
                # if database_name == DATABASE_REACTOME_CHEBI:
                #     data_df = data_df.set_index('ChEBI:' + data_df.index.astype(str))

                omics_data[dtype] = {
                    'df': data_df,
                    'fieldname': data_type_comp_fieldname
                }

        if len(omics_data) == 0:
            messages.warning(request, 'Add new inference failed. No data found.')
            return inference(request, analysis_id)

        form.fields['threshold'] = DecimalField(required=True, widget=TextInput(
            attrs={'autocomplete': 'off', 'type': 'number', 'min': '0', 'max': '1', 'step': '0.05',
                   'size': '10'}))
        form.fields['threshold'].initial = 0.0

        PVALUE_COLNAME = 'p-value'
        FOLD_CHANGE_COLNAME = 'fold_change'
        used_dtypes = []

        if form.is_valid():
            threshold = float(form.cleaned_data['threshold'])
            dfs = []
            for dtype in omics_data:
                res = omics_data[dtype]
                df = res['df']
                fieldname = res['fieldname']
                if fieldname in form.cleaned_data and len(form.cleaned_data[fieldname]) > 0:
                    colname = form.cleaned_data[fieldname]
                    padj_colname = PADJ_COL_PREFIX + colname
                    fc_colname = FC_COL_PREFIX + colname
                    df = df[[padj_colname, fc_colname]]
                    df = df.rename(columns={
                        padj_colname: PVALUE_COLNAME,
                        fc_colname: FOLD_CHANGE_COLNAME
                    })

                    # filter dataframe
                    df.dropna(inplace=True)
                    df = df[df[PVALUE_COLNAME] > threshold]  # filter dataframe by p-value threshold
                    df = df[FOLD_CHANGE_COLNAME].to_frame()  # convert series to dataframe

                    # scale features between (-1, 1) range
                    # df = 2 ** df
                    scaled_data = preprocessing.minmax_scale(df[FOLD_CHANGE_COLNAME], feature_range=(-1, 1))
                    df[FOLD_CHANGE_COLNAME] = scaled_data  # set scaled data back to the dataframe

                    dfs.append(df)
                    used_dtypes.append(dtype)

            df = pd.concat(dfs)
            logger.debug('Dataframe to send:')
            logger.debug(df)
            logger.debug(df.shape)

            # for debugging
            # df_out = os.path.join(BASE_DIR, 'static', 'data', 'debugging', 'reactome_df.csv')
            # df.to_csv(df_out, sep=',', header=True, index_label='#id', float_format='%.15f')
            # logger.debug('Written to %s' % df_out)

            # convert dataframe to tab-separated values
            # first column in the header has to start with a '#' sign
            # can't use scientific notation, so we format to %.15f
            data = df.to_csv(sep='\t', header=True, index_label='#id', float_format='%.15f')

            # get first species of this analysis
            analysis_species = analysis.get_species_list()
            assert len(analysis_species) >= 1
            if len(analysis_species) > 1:
                logger.warning('Multiple species detected. Using only the first species for analysis.')
            encoded_species = quote(analysis_species[0])
            logger.debug('Species: ' + encoded_species)

            # refer to https://reactome.org/AnalysisService/#/identifiers/getPostTextUsingPOST
            url = 'https://reactome.org/AnalysisService/identifiers/?interactors=false&species=' + encoded_species + \
                  '&sortBy=ENTITIES_PVALUE&order=ASC&resource=TOTAL&pValue=1&includeDisease=true'
            logger.debug('Reactome URL: ' + url)

            # make a POSt request to Reactome Analysis service
            response = requests.post(url, headers={'Content-Type': 'text/plain'}, data=data.encode('utf-8'))
            logger.debug('Response status code = %d' % response.status_code)

            # make sure the post request was successful
            if response.status_code != 200:
                messages.warning(request, 'Add new inference failed. Reactome Analysis Service returned status '
                                          'code %d' % response.status_code)
            else:  # success

                # see https://reactome.org/userguide/analysis for results explanation
                json_response = json.loads(response.text)
                token = json_response['summary']['token']
                reactome_url = 'https://reactome.org/PathwayBrowser/#DTAB=AN&ANALYSIS=' + token
                logger.debug('Pathway analysis token: ' + token)
                logger.debug('Pathway analysis URL: ' + reactome_url)

                pathways = json_response['pathways']
                # https://stackoverflow.com/questions/6027558/flatten-nested-dictionaries-compressing-keys
                pathways_df = pd.io.json.json_normalize(pathways, sep='_')
                logger.debug('Pathway analysis results:')
                logger.debug(pathways_df.columns.values)
                logger.debug(pathways_df)

                if pathways_df.empty:
                    messages.warning(request, 'Add new inference failed. No pathways returned by Reactome Analysis '
                                              'Service. Please check the logs.')
                else:
                    # as a quick hack, we put pathways df in the same format as PALS output
                    # this will let us use the update_pathway_analysis_data() method below
                    pathways_df = pathways_df[['stId', 'name', 'entities_fdr']].set_index('stId').rename(columns={
                        'name': 'pw_name',
                        'entities_fdr': 'REACTOME %s comb_p' % (colname)
                    })

                    # update reactome analysis results to database
                    pathway_analysis_data = get_last_analysis_data(analysis, PATHWAYS)
                    new_json_data = update_pathway_analysis_data(pathway_analysis_data, pathways_df)

                    new_data_type = pathway_analysis_data.data_type
                    display_data_type = ','.join([AddNewDataDict[dt] for dt in used_dtypes])
                    new_display_name = 'Reactome Analysis Service (%s): %s' % (display_data_type, colname)
                    new_metadata = {
                        'reactome_token': token,
                        'reactome_url': reactome_url
                    }
                    copy_analysis_data(analysis_data, new_json_data, new_display_name, new_metadata, new_data_type,
                                       INFERENCE_REACTOME)
                    messages.success(request, 'Add new inference successful.', extra_tags='primary')
                    return inference(request, analysis_id)

        else:
            messages.warning(request, 'Add new inference failed.')

    return inference(request, analysis_id)
