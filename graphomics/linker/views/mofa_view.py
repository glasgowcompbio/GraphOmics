import sys
from io import StringIO
import subprocess
import json
import base64
from PIL import Image

import pandas as pd
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django_select2.forms import Select2Widget

from django import forms
from linker.common import access_allowed
from linker.constants import *
from linker.forms import MofaResultForm
from linker.models import Analysis, AnalysisHistory

import mofax as mfx
from linker.views.functions import get_last_analysis_data, get_inference_data, save_analysis_history

from pyMultiOmics.mofax import MofaPipeline

def mofa_result(request, analysis_id, analysis_history_id):
    analysis = get_object_or_404(Analysis, pk=analysis_id)
    if not access_allowed(analysis, request):
        raise PermissionDenied()

    analysis_history_list = AnalysisHistory.objects.filter(analysis=analysis).order_by(
        'timestamp')
    list_data = get_mofa_list_data(analysis_id, analysis_history_id, analysis_history_list)

    if request.method == 'POST':
        form = MofaResultForm(request.POST)
        #analysis_data = get_last_analysis_data(analysis, data_type)

        if form.is_valid():
            result_type = int(request.POST['result'])

            if result_type == OVERVIEW:
                context = build_mofa_init_context(analysis, analysis_id, analysis_history_id)

            elif result_type == DETAIL:
                context = build_mofa_init_context(analysis, analysis_id, analysis_history_id)

                selected_form = MofaResultForm()
                view_choice, factor_choice = get_view_factor_choices(list_data)
                selected_form.fields['result'].initial = result_type
                selected_form.fields['view'] = forms.ChoiceField(required=True, choices=view_choice,
                                                                 widget=Select2Widget(attrs=SELECT_WIDGET_ATTRS))
                selected_form.fields['factor'] = forms.ChoiceField(required=True,
                                                                   choices=factor_choice,
                                                                   widget=Select2Widget(attrs=SELECT_WIDGET_ATTRS))

                action_url = reverse('mofa_detail_result_page', kwargs={
                    'analysis_id': analysis.id,
                    'analysis_history_id': analysis_history_id,
                })

                context['form'] = selected_form
                context['action_url'] = action_url

            elif result_type == COVARIANCE:
                context = build_mofa_init_context(analysis, analysis_id, analysis_history_id)

                selected_form = MofaResultForm()
                coviariance_choice = get_covariance_choices(analysis)
                selected_form.fields['result'].initial = result_type
                selected_form.fields['covariance'] = forms.ChoiceField(required=True,
                                                                       choices=coviariance_choice,
                                                                       widget=Select2Widget(attrs=SELECT_WIDGET_ATTRS))
                selected_form.fields['plot_type'] = forms.ChoiceField(required=True,
                                                                      choices=CovariancePlotTypeChoices,
                                                                      widget=Select2Widget(attrs=SELECT_WIDGET_ATTRS),
                                                                      label='Plot Type')

                action_url = reverse('mofa_coviariance_result_page_mid', kwargs={
                    'analysis_id': analysis.id,
                    'analysis_history_id': analysis_history_id,
                })

                context['form'] = selected_form
                context['action_url'] = action_url

            else:  # default
                context = build_mofa_init_context(analysis, analysis_id, analysis_history_id)

            return render(request, 'linker/explore_data_mofa.html', context)

        else:  # default
            context = build_mofa_init_context(analysis, analysis_id, analysis_history_id)
            return render(request, 'linker/explore_data_mofa.html', context)

    else:
        context = build_mofa_init_context(analysis, analysis_id, analysis_history_id)
        return render(request, 'linker/explore_data_mofa.html', context)

def mofa_detail_result(request, analysis_id, analysis_history_id):
    analysis = get_object_or_404(Analysis, pk=analysis_id)
    if not access_allowed(analysis, request):
        raise PermissionDenied()

    analysis_history_list = AnalysisHistory.objects.filter(analysis=analysis).order_by(
        'timestamp')
    list_data = get_mofa_list_data(analysis_id, analysis_history_id, analysis_history_list)
    mofa_filepath = list_data[0][0].inference_data['path']

    if request.method == 'POST':
        form = MofaResultForm(request.POST)
        view_choice, factor_choice = get_view_factor_choices(list_data)
        form.fields['view'] = forms.ChoiceField(required=True, choices=view_choice,
                                                widget=Select2Widget(attrs=SELECT_WIDGET_ATTRS))
        form.fields['factor'] = forms.ChoiceField(required=True,
                                                  choices=factor_choice,
                                                  widget=Select2Widget(attrs=SELECT_WIDGET_ATTRS))

        if form.is_valid():
            view = int(form.cleaned_data['view'])
            factor = int(form.cleaned_data['factor'])
            analysis_data = get_last_analysis_data(analysis, view)

            context = get_mofa_context_data(analysis, analysis_id, analysis_history_id, mofa_filepath, view, factor)

            result_df = get_result_df(context['mofa_result_df'], analysis_history_id, view, factor)

            mofa_info = {'view': view, 'factor': factor, 'history_id': analysis_history_id}
            inference_data = get_inference_data(view, None, None, result_df, metadata = mofa_info)
            display_name = None
            save_analysis_history(analysis_data, inference_data, display_name, INFERENCE_MOFA)

            action_url = reverse('mofa_detail_result_page', kwargs={
                'analysis_id': analysis_id,
                'analysis_history_id': analysis_history_id,
            })

            context['analysis_id'] = analysis_id
            context['analysis_history_id'] = analysis_history_id
            context['list_data'] = list_data
            context['form'] = form
            context['action_url'] = action_url

        else:
            context = build_mofa_init_context(analysis, analysis_id, analysis_history_id)

    else:
        context = build_mofa_init_context(analysis, analysis_id, analysis_history_id)

    return render(request, 'linker/explore_data_mofa.html', context)

def mofa_coviariance_result_mid(request, analysis_id, analysis_history_id):
    analysis = get_object_or_404(Analysis, pk=analysis_id)
    if not access_allowed(analysis, request):
        raise PermissionDenied()

    analysis_history_list = AnalysisHistory.objects.filter(analysis=analysis).order_by(
        'timestamp')
    list_data = get_mofa_list_data(analysis_id, analysis_history_id, analysis_history_list)

    if request.method == 'POST':
        form = MofaResultForm(request.POST)
        result_type = int(request.POST['result'])
        form.fields['result'].initial = result_type
        coviariance_choice = get_covariance_choices(analysis)
        form.fields['covariance'] = forms.ChoiceField(required=True,
                                                      choices=coviariance_choice,
                                                      widget=Select2Widget(attrs=SELECT_WIDGET_ATTRS))
        form.fields['plot_type'] = forms.ChoiceField(required=True,
                                                     choices=CovariancePlotTypeChoices,
                                                     widget=Select2Widget(attrs=SELECT_WIDGET_ATTRS),
                                                     label='Plot Type')

        if form.is_valid():
            plot_type = int(request.POST['plot_type'])

            action_url = reverse('mofa_coviariance_result_page', kwargs={
                'analysis_id': analysis.id,
                'analysis_history_id': analysis_history_id,
            })
            context = build_mofa_init_context(analysis, analysis_id, analysis_history_id)

            if plot_type in [FACTOR_COMBINATION, BOXPLOT]:
                view_choice, from_factor_choice = get_view_factor_choices(list_data)
                form.fields['from_factor'] = forms.ChoiceField(required=True,
                                                               choices=from_factor_choice,
                                                               widget=Select2Widget(attrs=SELECT_WIDGET_ATTRS),
                                                               label='From Factor')
                view_choice, to_factor_choice = get_view_factor_choices(list_data)
                form.fields['to_factor'] = forms.ChoiceField(required=True,
                                                             choices=to_factor_choice,
                                                             widget=Select2Widget(attrs=SELECT_WIDGET_ATTRS),
                                                             label='To Factor')

                context['form'] = form
                context['action_url'] = action_url

            elif plot_type == DIMENSION_REDUCTION:
                method_choices = zip(['TSNE', 'UMAP'], ['TSNE', 'UMAP'])
                form.fields['method'] = forms.ChoiceField(required=True,
                                                          choices=method_choices,
                                                          widget=Select2Widget(attrs=SELECT_WIDGET_ATTRS),
                                                          label='Reduction Method')
                context['form'] = form
                context['action_url'] = action_url

            else:  # default
                context = build_mofa_init_context(analysis, analysis_id, analysis_history_id)

            return render(request, 'linker/explore_data_mofa.html', context)

        else:  # default
            context = build_mofa_init_context(analysis, analysis_id, analysis_history_id)

        return render(request, 'linker/explore_data_mofa.html', context)

    else:  # default
        context = build_mofa_init_context(analysis, analysis_id, analysis_history_id)

    return render(request, 'linker/explore_data_mofa.html', context)


def mofa_coviariance_result(request, analysis_id, analysis_history_id):
    analysis = get_object_or_404(Analysis, pk=analysis_id)
    if not access_allowed(analysis, request):
        raise PermissionDenied()

    analysis_history_list = AnalysisHistory.objects.filter(analysis=analysis).order_by(
        'timestamp')
    list_data = get_mofa_list_data(analysis_id, analysis_history_id, analysis_history_list)
    mofa_filepath = list_data[0][0].inference_data['path']

    if request.method == 'POST':
        form = MofaResultForm(request.POST)
        covariance = str(request.POST['covariance'])
        plot_type = int(request.POST['plot_type'])

        coviariance_choice = get_covariance_choices(analysis)
        form.fields['covariance'] = forms.ChoiceField(required=True,
                                                      choices=coviariance_choice,
                                                      widget=Select2Widget(attrs=SELECT_WIDGET_ATTRS))
        form.fields['plot_type'] = forms.ChoiceField(required=True,
                                                     choices=CovariancePlotTypeChoices,
                                                     widget=Select2Widget(attrs=SELECT_WIDGET_ATTRS),
                                                     label='Plot Type')

        form.fields['covariance'].initial = covariance
        form.fields['plot_type'].initial = plot_type

        action_url = reverse('mofa_coviariance_result_page', kwargs={
            'analysis_id': analysis_id,
            'analysis_history_id': analysis_history_id,
        })

        context = {
            'mofa_filepath': mofa_filepath,
            'analysis_id': analysis_id,
            'analysis_history_id': analysis_history_id,
            'list_data': list_data,
            'action_url': action_url,
        }

        if plot_type == FACTOR_COMBINATION:
            view_choice, from_factor_choice = get_view_factor_choices(list_data)
            form.fields['from_factor'] = forms.ChoiceField(required=True,
                                                           choices=from_factor_choice,
                                                           widget=Select2Widget(attrs=SELECT_WIDGET_ATTRS),
                                                           label='From Factor')
            view_choice, to_factor_choice = get_view_factor_choices(list_data)
            form.fields['to_factor'] = forms.ChoiceField(required=True,
                                                         choices=to_factor_choice,
                                                         widget=Select2Widget(attrs=SELECT_WIDGET_ATTRS),
                                                         label='To Factor')
            if form.is_valid():
                from_factor = int(form.cleaned_data['from_factor'])
                to_factor = int(form.cleaned_data['to_factor'])

                covariance_plot = get_factor_combination_plot(analysis, analysis_id, analysis_history_id, mofa_filepath, covariance, from_factor, to_factor)

                context['form'] = form
                context['covariance_plot'] = covariance_plot

            else:
                context = build_mofa_init_context(analysis, analysis_id, analysis_history_id)

        elif plot_type == BOXPLOT:
            view_choice, from_factor_choice = get_view_factor_choices(list_data)
            form.fields['from_factor'] = forms.ChoiceField(required=True,
                                                           choices=from_factor_choice,
                                                           widget=Select2Widget(attrs=SELECT_WIDGET_ATTRS),
                                                           label='From Factor')
            view_choice, to_factor_choice = get_view_factor_choices(list_data)
            form.fields['to_factor'] = forms.ChoiceField(required=True,
                                                         choices=to_factor_choice,
                                                         widget=Select2Widget(attrs=SELECT_WIDGET_ATTRS),
                                                         label='To Factor')
            if form.is_valid():
                from_factor = int(form.cleaned_data['from_factor'])
                to_factor = int(form.cleaned_data['to_factor'])

                covariance_plot = get_boxplot(analysis, analysis_id, analysis_history_id, mofa_filepath, covariance, from_factor, to_factor)

                context['form'] = form
                context['covariance_plot'] = covariance_plot

            else:
                context = build_mofa_init_context(analysis, analysis_id, analysis_history_id)

        elif plot_type == DIMENSION_REDUCTION:
            method_choices = zip(['TSNE', 'UMAP'], ['TSNE', 'UMAP'])
            form.fields['method'] = forms.ChoiceField(required=True,
                                                      choices=method_choices,
                                                      widget=Select2Widget(attrs=SELECT_WIDGET_ATTRS),
                                                      label='Reduction Method')

            if form.is_valid():
                method = str(form.cleaned_data['method'])
                covariance_plot = get_dimension_reduction(analysis, analysis_id, analysis_history_id, mofa_filepath, covariance, method)
                context['form'] = form
                context['covariance_plot'] = covariance_plot

            else:
                context = build_mofa_init_context(analysis, analysis_id, analysis_history_id)
        else:
            context = build_mofa_init_context(analysis, analysis_id, analysis_history_id)
    else:
        context = build_mofa_init_context(analysis, analysis_id, analysis_history_id)

    return render(request, 'linker/explore_data_mofa.html', context)


def build_mofa_init_context(analysis, analysis_id, analysis_history_id):
    analysis_history_list = AnalysisHistory.objects.filter(analysis=analysis).order_by(
        'timestamp')
    list_data = get_mofa_list_data(analysis_id, analysis_history_id, analysis_history_list)
    mofa_filepath = list_data[0][0].inference_data['path']

    action_url = reverse('mofa_result_page', kwargs={
        'analysis_id': analysis_id,
        'analysis_history_id': analysis_history_id,
    })
    base_form = MofaResultForm()

    m = build_mofapipeline(mofa_filepath)
    plot_factors = get_plot_factors(m)
    plot_factors_correlation = get_plot_factors_correlation(m)
    plot_r2 = get_plot_r2(m)
    data_overview_plot = get_data_overview_plot(analysis_id, analysis_history_id, mofa_filepath)
    factor_covariance_plot = get_factor_covariance_plot(analysis, analysis_id, analysis_history_id, mofa_filepath)

    context = {
        'mofa_filepath': mofa_filepath,
        'analysis_id': analysis_id,
        'analysis_history_id': analysis_history_id,
        'list_data': list_data,
        'form': base_form,
        'action_url': action_url,
        'plot_factors': plot_factors,
        'plot_factors_correlation': plot_factors_correlation,
        'plot_r2': plot_r2,
        'data_overview_plot': data_overview_plot,
    }

    if factor_covariance_plot != None:
        context['factor_covariance_plot'] = factor_covariance_plot
    else:
        context['message'] = 'No metadata applied!'

    return context

def get_mofa_context_data(analysis, analysis_id, analysis_history_id, mofa_filepath, view, factor):
    m = build_mofapipeline(mofa_filepath)

    message = 'Result!'
    if view == GENOMICS:
        view = 'genes'
    elif view == PROTEOMICS:
        view = 'proteins'
    elif view == METABOLOMICS:
        view = 'compounds'
    else:
        message = 'Invalid input!'

    top_feature_df = get_top_feature_df(m, view, factor)
    if not isinstance(top_feature_df, pd.DataFrame):
        message = 'Invalid input!'
    top_feature_df_list = get_json_df(top_feature_df.head(20))

    top_feature_plot = get_top_feature_plot(m, view, factor)
    if top_feature_plot == None:
        message = 'Invalid input!'

    heatmap = get_heatmap(analysis, analysis_id, analysis_history_id, mofa_filepath, view, factor)

    context = {
        'mofa_filepath': mofa_filepath,
        'mofa_df': top_feature_df_list,
        'mofa_fig': top_feature_plot,
        'message': message,
        'mofa_result_df': top_feature_df,
        'heatmap': heatmap
    }

    return context


def get_view_factor_choices(list_data):
    trained_views = list_data[0][0].inference_data['views']
    nFactor = list_data[0][0].inference_data['nFactor']

    view_choice_dict = {GENOMICS: 'Gene Data', PROTEOMICS: 'Protein Data', METABOLOMICS: 'Compound Data'}
    view_choice_list_int = [None]
    view_choice_list_str = [NA]
    for i in trained_views:
        view_choice_list_int.append(i)
        view_choice_list_str.append(view_choice_dict[i])
    view_choice = zip(view_choice_list_int, view_choice_list_str)
    factor_choice = zip(range(1, nFactor + 1), range(1, nFactor + 1))

    return view_choice, factor_choice


def get_covariance_choices(analysis):
    covariance_choice_list = [None]
    covariance_choice_list_str = [NA]
    if analysis.has_metadata():
        metadata_path = analysis.get_metadata_path()
        metadata = pd.read_csv(metadata_path, index_col='sample')
        for col in metadata.columns:
            covariance_choice_list.append(col)
            covariance_choice_list_str.append(col)
    covariance_choices = zip(covariance_choice_list, covariance_choice_list_str)
    return covariance_choices


def get_top_feature_df(m, view, factor):
    mofa = m.mofa
    factor = factor - 1

    shape = len(mofa.model['features'][view])
    try:
        df = mofa.get_top_features(views=view, factors=factor, n_features=shape, df=True)
        return df
    except:
        return None

def get_json_df(df):
    if isinstance(df, pd.DataFrame):
        json_records = df.reset_index().to_json(orient='records')
        top_feature_df = []
        top_feature_df = json.loads(json_records)
        return top_feature_df
    else:
        return None

def get_top_feature_plot(m, view, factor):
    factor = factor - 1
    try:
        fig = m.plot_top_features(factors=factor, views=view, n_features=20)
        imgdata = StringIO()
        fig.figure.savefig(imgdata, format='svg')
        imgdata.seek(0)
        top_feature_plot = imgdata.getvalue()

        return top_feature_plot

    except:
        return None

def get_data_overview_plot(analysis_id, analysis_history_id, filepath):
    path = make_image_dirctory(analysis_id, analysis_history_id)

    out_path = os.path.join(path, str(analysis_history_id))
    r_command = 'Rscript --vanilla linker/Rscript/mofa_plot.R -f %s -t data_overview -o %s' % (filepath, out_path)
    subprocess.run(r_command, shell=True)
    data_overview_plot_path = out_path + "_data_overview.png"
    data_uri = base64.b64encode(open(data_overview_plot_path, 'rb').read()).decode('utf-8')
    data_overview_plot = 'data:image/png;base64,{0}'.format(data_uri)
    return data_overview_plot

def get_factor_covariance_plot(analysis, analysis_id, analysis_history_id, filepath):
    if analysis.has_metadata():
        metadata_path = analysis.get_metadata_path()
        metadata = pd.read_csv(metadata_path, index_col='sample')

        if len(metadata.columns) >= 2 and 'group' in metadata.columns:
            path = make_image_dirctory(analysis_id, analysis_history_id)
            out_path = os.path.join(path, str(analysis_history_id))
            r_command = 'Rscript --vanilla linker/Rscript/mofa_plot.R -f %s -d %s -t correlate_factors_with_covariates -o %s' % (filepath, metadata_path, out_path)
            subprocess.run(r_command, shell=True)
            factor_covariance_plot_path = out_path + "_correlate_factors_with_covariates.png"
            data_uri = base64.b64encode(open(factor_covariance_plot_path, 'rb').read()).decode('utf-8')
            factor_covariance_plot = 'data:image/png;base64,{0}'.format(data_uri)
            return factor_covariance_plot

        else:
            return None
    else:
        return None

def get_dimension_reduction(analysis, analysis_id, analysis_history_id, mofa_filepath, covariance, method):
    if analysis.has_metadata():
        metadata_path = analysis.get_metadata_path()
        metadata = pd.read_csv(metadata_path, index_col='sample')

        if covariance in metadata.columns and 'group' in metadata.columns:
            path = make_image_dirctory(analysis_id, analysis_history_id)
            out_path = os.path.join(path, str(analysis_history_id))
            r_command = 'Rscript --vanilla linker/Rscript/mofa_plot.R -f %s -d %s -t dimension_reduction -c %s -u %s -o %s' % (
            mofa_filepath, metadata_path, covariance, method, out_path)
            subprocess.run(r_command, shell=True)
            out_path_list = [out_path, covariance, method, "dimension_reduction.png"]
            dimension_reduction_path = '_'.join(out_path_list)
            data_uri = base64.b64encode(open(dimension_reduction_path, 'rb').read()).decode('utf-8')
            dimension_reduction = 'data:image/png;base64,{0}'.format(data_uri)
            return dimension_reduction

        else:
            return None
    else:
        return None


def get_boxplot(analysis, analysis_id, analysis_history_id, mofa_filepath, covariance, from_factor, to_factor):
    if analysis.has_metadata():
        metadata_path = analysis.get_metadata_path()
        metadata = pd.read_csv(metadata_path, index_col='sample')

        if covariance in metadata.columns and 'group' in metadata.columns:
            path = make_image_dirctory(analysis_id, analysis_history_id)
            out_path = os.path.join(path, str(analysis_history_id))
            r_command = 'Rscript --vanilla linker/Rscript/mofa_plot.R -f %s -d %s -c %s -t boxplot -x %d -y %d -o %s' % (
            mofa_filepath, metadata_path, covariance, from_factor, to_factor, out_path)
            subprocess.run(r_command, shell=True)
            out_path_list = [out_path, covariance, str(from_factor), str(to_factor), "boxplot.png"]
            boxplot_path = '_'.join(out_path_list)
            data_uri = base64.b64encode(open(boxplot_path, 'rb').read()).decode('utf-8')
            boxplot = 'data:image/png;base64,{0}'.format(data_uri)
            return boxplot

        else:
            return None
    else:
        return None


def get_factor_combination_plot(analysis, analysis_id, analysis_history_id, mofa_filepath, covariance, from_factor, to_factor):
    if analysis.has_metadata():
        metadata_path = analysis.get_metadata_path()
        metadata = pd.read_csv(metadata_path, index_col='sample')

        if covariance in metadata.columns and 'group' in metadata.columns:
            path = make_image_dirctory(analysis_id, analysis_history_id)
            out_path = os.path.join(path, str(analysis_history_id))
            r_command = 'Rscript --vanilla linker/Rscript/mofa_plot.R -f %s -d %s -c %s -t factor_combination_plot -x %d -y %d -o %s' % (
            mofa_filepath, metadata_path, covariance, from_factor, to_factor, out_path)
            subprocess.run(r_command, shell=True)
            out_path_list = [out_path, covariance, str(from_factor), str(to_factor), "factor_combination_plot.png"]
            factor_combination_plot_path = '_'.join(out_path_list)
            data_uri = base64.b64encode(open(factor_combination_plot_path, 'rb').read()).decode('utf-8')
            factor_combination_plot = 'data:image/png;base64,{0}'.format(data_uri)
            return factor_combination_plot

        else:
            return None
    else:
        return None

def get_heatmap(analysis, analysis_id, analysis_history_id, mofa_filepath, view, factor):
    path = make_image_dirctory(analysis_id, analysis_history_id)
    out_path = os.path.join(path, str(analysis_history_id))
    r_command = 'Rscript --vanilla linker/Rscript/mofa_plot.R -f %s -v %s -x %d -t heatmap -o %s' % (mofa_filepath, view, factor, out_path)
    subprocess.run(r_command, shell=True)
    out_path_list = [out_path, view, str(factor), "heatmap.png"]
    heatmap_path = '_'.join(out_path_list)
    data_uri = base64.b64encode(open(heatmap_path, 'rb').read()).decode('utf-8')
    heatmap = 'data:image/png;base64,{0}'.format(data_uri)
    return heatmap


def get_plot_factors(m):
    mofa = m.mofa
    fig = mfx.plot_factors_violin(mofa)
    imgdata = StringIO()
    fig.figure.savefig(imgdata, format='svg')
    imgdata.seek(0)
    plot_factors = imgdata.getvalue()

    return plot_factors

def get_plot_factors_correlation(m):
    mofa = m.mofa
    fig = mfx.plot_factors_correlation(mofa)
    imgdata = StringIO()
    fig.figure.savefig(imgdata, format='svg')
    imgdata.seek(0)
    plot_factors_correlation = imgdata.getvalue()

    return plot_factors_correlation

def get_plot_r2(m):
    mofa = m.mofa
    fig = mfx.plot_r2(mofa)
    imgdata = StringIO()
    fig.figure.savefig(imgdata, format='svg')
    imgdata.seek(0)
    plot_r2 = imgdata.getvalue()

    return plot_r2


def get_mofa_list_data(analysis_id, analysis_history_id, analysis_history_list):
    list_data = []
    for analysis_history in analysis_history_list:
        inference_type = analysis_history.inference_type
        history_id = analysis_history.id
        click_url_1 = None

        if inference_type == INFERENCE_MOFA and history_id == analysis_history_id:
            click_url_1 = reverse('explore_data', kwargs={
                'analysis_id': analysis_id,
            })
            break

    item = [analysis_history, click_url_1]
    list_data.append(item)
    return list_data


def get_result_df(df, history_id, view, factor):
    d = {0: 'genes', 2: 'proteins', 3: 'compounds'}
    df.set_index('feature', inplace=True)
    df.drop(['index', 'factor', 'value_abs', 'view'], axis=1, inplace=True)
    label = 'weight_%s_factor%s_%s' % (str(d[view]), str(factor), str(history_id))
    df.columns = [label]
    return df


def build_mofapipeline(mofa_filepath):
    m = MofaPipeline()
    m.load_mofa(mofa_filepath)
    m.build_mofa()

    return m

def make_image_dirctory(analysis_id, analysis_history_id):
    folder_name = 'analysis_upload_' + str(analysis_id)
    path = os.path.abspath(os.path.join('media', folder_name, 'images', str(analysis_history_id)))
    command = 'mkdir -p ' + path
    subprocess.run(command, shell=True)
    return path

