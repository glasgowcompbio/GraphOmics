from io import StringIO
import mofax as mfx

import json
import jsonpickle
import numpy as np
from django import forms
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.forms import TextInput, DecimalField
from django.shortcuts import render, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic import TemplateView, DeleteView
from django_select2.forms import Select2Widget
from loguru import logger
from sklearn.decomposition import PCA as skPCA

from linker.common import access_allowed
from linker.constants import *
from linker.forms import BaseInferenceForm
from linker.models import Analysis, AnalysisData, AnalysisHistory
from linker.views.functions import get_last_analysis_data, get_groups, get_dataframes, get_standardized_df, \
    get_group_members, fig_to_div, get_inference_data, save_analysis_history
from linker.views.pathway_analysis import get_pals_data_source, run_pals, run_ora, \
    run_gsea
from linker.views.pipelines import GraphOmicsInference, MofaInference
from linker.views.reactome_analysis import get_omics_data, populate_reactome_choices, get_used_dtypes, get_data, \
    to_expression_tsv, get_analysis_first_species, parse_reactome_json, send_to_reactome, get_first_analysis_history_id, \
    to_ora_tsv

def inference(request, analysis_id):
    analysis = get_object_or_404(Analysis, pk=analysis_id)
    if not access_allowed(analysis, request):
        raise PermissionDenied()

    analysis_history_list = AnalysisHistory.objects.filter(analysis=analysis).order_by(
        'timestamp')
    list_data = get_list_data(analysis_id, analysis_history_list)

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
                selected_form.fields['min_hits'] = forms.IntegerField(min_value=0, initial=PLAGE_MIN_HITS,
                                                                      label='Minimum hits')

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
                selected_form.fields['threshold'].initial = 0.05

                action_url = reverse('inference_reactome', kwargs={
                    'analysis_id': analysis_id,
                })

            elif inference_type == INFERENCE_MOFA:
                action_url = reverse('inference_mofa', kwargs={
                    'analysis_id': analysis_id,
                })
                if data_type == MULTI_OMICS:
                    for dtype in [GENOMICS, PROTEOMICS, METABOLOMICS]:
                        analysis_data = get_last_analysis_data(analysis, dtype)
                else:
                    analysis_data = get_last_analysis_data(analysis, data_type)

                selected_form = BaseInferenceForm()
                selected_form.fields['data_type'].initial = data_type
                selected_form.fields['inference_type'].initial = inference_type
                selected_form.fields['Use uploaded .hdf5 file'] = forms.ChoiceField(choices=zip(['Yes', 'No'], ['Yes', 'No']), widget=Select2Widget())

                selected_form.fields['Number of Factor'] = forms.IntegerField(required=True, widget=forms.TextInput(attrs={'size': 100}))
                selected_form.fields['Scale View'] = forms.ChoiceField(required=False, choices=zip([True, False], ['Yes', 'No']), widget=Select2Widget())
                selected_form.fields['Scale Group'] = forms.ChoiceField(required=False, choices=zip([True, False], ['Yes', 'No']), widget=Select2Widget())

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


def get_case_control_form(data_type, groups, inference_type):
    selected_form = BaseInferenceForm()
    selected_form.fields['data_type'].initial = data_type
    selected_form.fields['inference_type'].initial = inference_type
    selected_form.fields['case'] = forms.ChoiceField(choices=groups,
                                                     widget=Select2Widget(SELECT_WIDGET_ATTRS))
    selected_form.fields['control'] = forms.ChoiceField(choices=groups,
                                                        widget=Select2Widget(SELECT_WIDGET_ATTRS))
    return selected_form


def get_list_data(analysis_id, analysis_history_list):
    list_data = []
    for analysis_history in analysis_history_list:
        inference_type = analysis_history.inference_type
        click_url_1 = None
        click_url_2 = None

        # when clicked, go to the Explore Data page
        if inference_type == INFERENCE_T_TEST or \
                inference_type == INFERENCE_DESEQ or \
                inference_type == INFERENCE_LIMMA or \
                inference_type == INFERENCE_PALS or \
                inference_type == INFERENCE_ORA or \
                inference_type == INFERENCE_GSEA:
            click_url_1 = reverse('explore_data', kwargs={
                'analysis_id': analysis_id,
            })

        # when clicked, show the Explore Analysis Data page
        elif inference_type == INFERENCE_PCA:
            click_url_1 = reverse('pca_result', kwargs={
                'analysis_id': analysis_id,
                'analysis_data_id': analysis_history.analysis_data.id,
                'analysis_history_id': analysis_history.id
            })

        # when clicked, go to Reactome
        elif inference_type == INFERENCE_REACTOME:
            if REACTOME_ORA_URL in analysis_history.inference_data and REACTOME_EXPR_URL in analysis_history.inference_data:
                click_url_1 = analysis_history.inference_data[REACTOME_ORA_URL]
                click_url_2 = analysis_history.inference_data[REACTOME_EXPR_URL]

        elif inference_type == INFERENCE_MOFA:
            history_id = analysis_history.id
            click_url_1 = reverse('mofa_result_page', kwargs={
                'analysis_id': analysis_id,
                'analysis_history_id': history_id
            })

        item = [analysis_history, click_url_1, click_url_2]
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
            wi = GraphOmicsInference(data_df, design_df, data_type, min_value=min_replace)
            result_df = wi.run_ttest(case, control)

            # create a new analysis data
            display_name = 't-test: %s_vs_%s' % (case, control)
            inference_data = get_inference_data(data_type, case, control, result_df)
            save_analysis_history(analysis_data, inference_data, display_name, INFERENCE_T_TEST)
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
            wi = GraphOmicsInference(data_df, design_df, data_type)
            try:
                pd_df, rld_df, res_ordered = wi.run_deseq(MIN_REPLACE_GENOMICS, case, control)
            except Exception as e:
                logger.warning('Failed to run DESeq2: %s' % str(e))
                messages.warning(request, 'Add new inference failed.')
                return inference(request, analysis_id)
            result_df = pd_df[['padj', 'log2FoldChange']]

            # create a new analysis data
            display_name = 'DESeq2: %s_vs_%s' % (case, control)
            metadata = {
                'rld_df': rld_df.to_json(),
                'res_ordered': jsonpickle.encode(res_ordered)
            }
            inference_data = get_inference_data(data_type, case, control, result_df, metadata=metadata)
            save_analysis_history(analysis_data, inference_data, display_name, INFERENCE_DESEQ)
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
            wi = GraphOmicsInference(data_df, design_df, data_type, min_value=min_replace)
            result_df = wi.run_limma(case, control)

            # create a new analysis data
            display_name = 'limma: %s_vs_%s' % (case, control)
            inference_data = get_inference_data(data_type, case, control, result_df)
            save_analysis_history(analysis_data, inference_data, display_name, INFERENCE_LIMMA)
            messages.success(request, 'Add new inference successful.', extra_tags='primary')
            return inference(request, analysis_id)
        else:
            messages.warning(request, 'Add new inference failed.')

    return inference(request, analysis_id)


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
                inference_data = get_inference_data(data_type, None, None, None, metadata)
                save_analysis_history(analysis_data, inference_data, display_name, INFERENCE_PCA)
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
        analysis_history_id = self.kwargs['analysis_history_id']
        analysis_data = AnalysisData.objects.get(pk=analysis_data_id)
        analysis_history = AnalysisHistory.objects.get(pk=analysis_history_id)
        inference_data = analysis_history.inference_data

        n_components = jsonpickle.loads(inference_data['pca_n_components'])
        X_std_index = jsonpickle.loads(inference_data['pca_X_std_index'])
        X_proj = jsonpickle.loads(inference_data['pca_X_proj'])
        var_exp = jsonpickle.loads(inference_data['pca_var_exp'])

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
        form.fields['min_hits'] = forms.IntegerField(min_value=0, initial=PLAGE_MIN_HITS,
                                                     label='Minimum hits')

        if form.is_valid():
            case = form.cleaned_data['case']
            control = form.cleaned_data['control']
            min_hits = form.cleaned_data['min_hits']

            # get pals data source from the current analysis_data
            pals_data_source = get_pals_data_source(analysis, analysis_data, case, control, min_hits)
            if pals_data_source is None:
                messages.warning(request, 'Add new inference failed. No data found.')
                return inference(request, analysis_id)

            # run pals
            pals_df = run_pals(pals_data_source)

            # check for NaN in the results. It shouldn't happen.
            if pals_df.isnull().values.any():
                logger.warning('PALS result contains NaN! These rows will be deleted.')
                logger.warning(pals_df[pals_df.isnull().any(axis=1)])
                pals_df = pals_df.dropna()

            # update PALS results to database
            pathway_analysis_data = get_last_analysis_data(analysis, PATHWAYS)
            inference_data = get_inference_data(data_type, case, control, pals_df)
            display_name = 'PLAGE %s: %s_vs_%s' % (pals_data_source.database_name, case, control)
            save_analysis_history(pathway_analysis_data, inference_data, display_name, INFERENCE_PALS)
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
            pals_data_source = get_pals_data_source(analysis, analysis_data, case, control, 0)
            if pals_data_source is None:
                messages.warning(request, 'Add new inference failed. No data found.')
                return inference(request, analysis_id)

            # run ora
            pals_df = run_ora(pals_data_source)

            # update ORA results to database
            pathway_analysis_data = get_last_analysis_data(analysis, PATHWAYS)
            inference_data = get_inference_data(data_type, case, control, pals_df)
            display_name = 'ORA %s: %s_vs_%s' % (pals_data_source.database_name, case, control)
            save_analysis_history(pathway_analysis_data, inference_data, display_name, INFERENCE_ORA)
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
            pals_data_source = get_pals_data_source(analysis, analysis_data, case, control, 0)
            if pals_data_source is None:
                messages.warning(request, 'Add new inference failed. No data found.')
                return inference(request, analysis_id)

            # run gse
            pals_df = run_gsea(pals_data_source)

            # update GSEA results to database
            pathway_analysis_data = get_last_analysis_data(analysis, PATHWAYS)
            inference_data = get_inference_data(data_type, case, control, pals_df)
            display_name = 'GSEA %s: %s_vs_%s' % (pals_data_source.database_name, case, control)
            save_analysis_history(pathway_analysis_data, inference_data, display_name, INFERENCE_GSEA)

            messages.success(request, 'Add new inference successful.', extra_tags='primary')
            return inference(request, analysis_id)

        else:
            messages.warning(request, 'Add new inference failed.')

    return inference(request, analysis_id)


def inference_reactome(request, analysis_id):
    if request.method == 'POST':
        analysis = get_object_or_404(Analysis, pk=analysis_id)
        form = BaseInferenceForm(request.POST)

        # if data type is MULTI_OMICS, then turn it into GENOMICS, PROTEOMICS and METABOLOMICS
        data_type = int(request.POST['data_type'])
        data_types = [data_type]
        if data_type == MULTI_OMICS:
            data_types = [GENOMICS, PROTEOMICS, METABOLOMICS]

        # make sure actually we have some data
        analysis_data, omics_data = get_omics_data(analysis, data_types, form)
        if len(omics_data) == 0:
            messages.warning(request, 'Add new inference failed. No data found.')
            return inference(request, analysis_id)

        # reinitialise the threshold field
        form.fields['threshold'] = DecimalField(required=True, widget=TextInput(
            attrs={'autocomplete': 'off', 'type': 'number', 'min': '0', 'max': '1', 'step': '0.05',
                   'size': '10'}))
        form.fields['threshold'].initial = 0.05

        if form.is_valid():
            form_data = form.cleaned_data
            threshold = float(form_data['threshold'])
            used_dtypes = get_used_dtypes(form_data, omics_data)
            encoded_species = get_analysis_first_species(analysis)

            # get ORA and expression data to send to reactome
            logger.debug('Preparing ORA data')
            ora_df = get_data(form_data, omics_data, used_dtypes, threshold)
            ora_data = to_ora_tsv(ora_df.index.values)
            logger.debug(ora_df.index.values)
            logger.debug(ora_df.index.values.shape)

            logger.debug('Preparing expression data')
            expression_df = get_data(form_data, omics_data, used_dtypes,
                                     1.0)  # use large threshold to show all entities
            expression_data = to_expression_tsv(expression_df)
            logger.debug(expression_df)
            logger.debug(expression_df.shape)

            # POST the data to Reactome Analysis Service
            logger.debug('POSTing ORA data')
            ora_status_code, ora_json_response = send_to_reactome(ora_data, encoded_species)

            logger.debug('POSTing expression data')
            expr_status_code, expr_json_response = send_to_reactome(expression_data, encoded_species)

            # ensure that both POST requests are successful
            if ora_status_code != 200 or expr_status_code != 200:
                messages.warning(request, 'Add new inference failed. Reactome Analysis Service returned status '
                                          'code %d and %d' % (ora_status_code, expr_status_code))
            else:  # success 200 for both
                assert ora_json_response is not None
                assert expr_json_response is not None

                # parse FDR values for pathways from ORA results
                logger.debug('Parsing ORA results')
                pathways_df, ora_reactome_url, ora_token = parse_reactome_json(ora_json_response)
                logger.debug(pathways_df.columns.values)
                logger.debug(pathways_df)

                logger.debug('Parsing expression results')
                _, expr_reactome_url, expr_token = parse_reactome_json(expr_json_response)

                if not pathways_df.empty:
                    first_analysis_history_id = get_first_analysis_history_id(form_data, omics_data, used_dtypes)
                    first_analysis_history = AnalysisHistory.objects.get(pk=first_analysis_history_id)
                    case = first_analysis_history.inference_data['case']
                    control = first_analysis_history.inference_data['control']
                    comparison_name = '%s_vs_%s' % (case, control)

                    # as a quick hack, we put pathways df in the same format as PALS output
                    # this will let us use the update_pathway_analysis_data() method below
                    pathways_df = pathways_df[['stId', 'name', 'entities_fdr']].set_index('stId').rename(columns={
                        'name': 'pw_name',
                        'entities_fdr': 'REACTOME %s comb_p' % (comparison_name)
                    })
                    pathway_analysis_data = get_last_analysis_data(analysis, PATHWAYS)

                    # save the updated analysis data to database
                    display_data_type = ','.join([AddNewDataDict[dt] for dt in used_dtypes])
                    display_name = 'Reactome Analysis Service (%s): %s' % (display_data_type, comparison_name)
                    metadata = {
                        REACTOME_ORA_TOKEN: ora_token,
                        REACTOME_ORA_URL: ora_reactome_url,
                        REACTOME_EXPR_TOKEN: expr_token,
                        REACTOME_EXPR_URL: expr_reactome_url
                    }
                    inference_data = get_inference_data(data_type, None, None, pathways_df, metadata=metadata)
                    save_analysis_history(pathway_analysis_data, inference_data, display_name, INFERENCE_REACTOME)
                    messages.success(request, 'Add new inference successful.', extra_tags='primary')
                    return inference(request, analysis_id)

                else:
                    messages.warning(request, 'Add new inference failed. No pathways returned by Reactome Analysis '
                                              'Service. Please check the logs.')

        else:
            messages.warning(request, 'Add new inference failed.')

    return inference(request, analysis_id)


def inference_mofa(request, analysis_id):
    if request.method == 'POST':
        analysis = get_object_or_404(Analysis, pk=analysis_id)

        analysis_history_list = AnalysisHistory.objects.filter(analysis=analysis).order_by(
            'timestamp')
        history_id = 0
        for history in analysis_history_list:
            history_id = history.id

        form = BaseInferenceForm(request.POST)
        data_type = int(request.POST['data_type'])
        data_types = [data_type]
        if data_type == MULTI_OMICS:
            data_types = [GENOMICS, PROTEOMICS, METABOLOMICS]
        analysis_data, omics_data = get_omics_data(analysis, data_types, form)

        form.fields['Use uploaded .hdf5 file'] = forms.ChoiceField(choices=zip(['Yes', 'No'], ['Yes', 'No']), widget=Select2Widget())
        form.fields['Number of Factor'] = forms.IntegerField(required=True, widget=forms.TextInput(attrs={'size': 100}))
        form.fields['Scale View'] = forms.ChoiceField(required=False, choices=zip([True, False], ['Yes', 'No']), widget=Select2Widget())
        form.fields['Scale Group'] = forms.ChoiceField(required=False, choices=zip([True, False], ['Yes', 'No']), widget=Select2Widget())

        if form.is_valid():
            up_data = form.cleaned_data['Use uploaded .hdf5 file']

            mofa_info = {}
            filePath = ''
            if up_data == 'Yes':
                if analysis.has_mofa_data():
                    filePath = analysis.analysisupload.mofa_data.path
                    display_name = 'MOFA: uploaded hdf5 file'
                    numFactor = form.cleaned_data['Number of Factor']
                    mofa_info['nFactor'] = numFactor
                else:
                    messages.warning(request, 'No .hdf5 file found.')

            else:
                numFactor = form.cleaned_data['Number of Factor']
                scale_view = form.cleaned_data['Scale View'] in ['True']
                scale_group = form.cleaned_data['Scale Group'] in ['True']

                mofa = MofaInference(analysis, data_type, numFactor, scale_view, scale_group)
                filePath, trained_views = mofa.run_mofa()
                display_name = 'MOFA: %s Factors' % numFactor
                mofa_info['nFactor'] = numFactor
                mofa_info['views'] = trained_views

            mofa_info['path'] = filePath
            history_id += 1
            mofa_info['history_id'] = history_id

            #analysis.set_mofa_hdf5_path(filePath)
            inference_data = get_inference_data(data_type, None, None, None, metadata = mofa_info)
            save_analysis_history(analysis_data, inference_data, display_name, INFERENCE_MOFA)
            messages.success(request, 'Add new inference successful.', extra_tags='primary')

        else:
            messages.warning(request, 'Add new inference failed.')

    return inference(request, analysis_id)


class DeleteAnalysisHistoryView(DeleteView):
    model = AnalysisHistory
    success_url = reverse_lazy('inference')
    template_name = 'linker/confirm_delete_analysis_history.html'
    success_message = "Analysis history was successfully deleted."

    # https://stackoverflow.com/questions/24822509/success-message-in-deleteview-not-shown/42656041#42656041
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super(DeleteAnalysisHistoryView, self).delete(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy('inference', kwargs={'analysis_id': self.object.analysis_data.analysis.pk})
