from io import StringIO

import json

import pandas as pd
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django_select2.forms import Select2Widget

from linker import forms
from linker.common import access_allowed
from linker.constants import *
from linker.forms import MofaResultForm
from linker.models import Analysis, AnalysisHistory

import mofax as mfx
import sys

from linker.views.functions import get_last_analysis_data, get_inference_data, save_mofa_analysis_history

sys.path.append('/path/to/pyMultiOmics')
from pyMultiOmics.mofax import MofaPipeline

def mofa_result(request, analysis_id):
    analysis = get_object_or_404(Analysis, pk=analysis_id)
    mofa_filepath = analysis.get_mofa_hdf5_path()
    if not access_allowed(analysis, request):
        raise PermissionDenied()

    analysis_history_list = AnalysisHistory.objects.filter(analysis=analysis).order_by(
        'timestamp')
    list_data = get_mofa_list_data(analysis_id, analysis_history_list)


    if request.method == 'POST':
        form = MofaResultForm(request.POST)
        data_type = int(request.POST['view'])
        analysis_data = get_last_analysis_data(analysis, data_type)

        if form.is_valid():
            view = int(form.cleaned_data['view'])
            factor = int(form.cleaned_data['factor'])

            context = get_mofa_context_data(mofa_filepath, view, factor)

            result_df = get_result_df(context['mofa_result_df'], view, factor)
            inference_data = get_inference_data(data_type, view, factor, result_df)
            #display_name = 'MOFA Top Features for View %s Factor %s' % (str(view), str(factor))
            save_mofa_analysis_history(analysis_data, inference_data, INFERENCE_MOFA)

            action_url = reverse('mofa_result_page', kwargs={
                'analysis_id': analysis_id,
            })
            selected_form = MofaResultForm()
            selected_form.fields['view'].initial = view
            selected_form.fields['factor'].initial = factor

            context['analysis_id'] = analysis.pk
            context['list_data'] = list_data
            context['form'] = selected_form
            context['action_url'] = action_url

            return render(request, 'linker/explore_data_mofa.html', context)

        else:  # default
            action_url = reverse('mofa_result_page', kwargs={
                'analysis_id': analysis_id,
            })
            selected_form = MofaResultForm(request.POST)

            context = {
                'mofa_filepath': mofa_filepath,
                'analysis_id': analysis.pk,
                'list_data': list_data,
                'form': selected_form,
                'action_url': action_url
            }
            return render(request, 'linker/explore_data_mofa.html', context)

    else:
        context = build_mofa_init_context(analysis)
        return render(request, 'linker/explore_data_mofa.html', context)

def build_mofa_init_context(analysis):
    mofa_filepath = analysis.get_mofa_hdf5_path()
    analysis_history_list = AnalysisHistory.objects.filter(analysis=analysis).order_by(
        'timestamp')
    list_data = get_mofa_list_data(analysis.id, analysis_history_list)

    action_url = reverse('mofa_result_page', kwargs={
        'analysis_id': analysis.id,
    })
    base_form = MofaResultForm()

    m = build_mofapipeline(mofa_filepath)
    plot_factors = get_plot_factors(m)
    plot_factors_correlation = get_plot_factors_correlation(m)
    plot_r2 = get_plot_r2(m)

    context = {
        'mofa_filepath': mofa_filepath,
        'analysis_id': analysis.pk,
        'list_data': list_data,
        'form': base_form,
        'action_url': action_url,
        'plot_factors': plot_factors,
        'plot_factors_correlation': plot_factors_correlation,
        'plot_r2': plot_r2
    }
    return context

def get_mofa_context_data(mofa_filepath, view, factor):
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
    top_feature_df_list = get_json_df(top_feature_df)

    top_feature_plot = get_top_feature_plot(m, view, factor)
    if top_feature_plot == None:
        message = 'Invalid input!'

    context = {
        'mofa_filepath': mofa_filepath,
        'mofa_df': top_feature_df_list,
        'mofa_fig': top_feature_plot,
        'message': message,
        'mofa_result_df': top_feature_df
    }

    return context


def get_top_feature_df(m, view, factor):
    mofa = m.mofa
    factor = factor - 1
    try:
        df = mofa.get_top_features(views=view, factors=factor, n_features=10, df=True)
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
        fig = m.plot_top_features(factors=factor, views=view, n_features=10)
        imgdata = StringIO()
        fig.figure.savefig(imgdata, format='svg')
        imgdata.seek(0)
        top_feature_plot = imgdata.getvalue()

        return top_feature_plot

    except:
        return None

def get_plot_factors(m):
    mofa = m.mofa
    fig = mfx.plot_factors(mofa)
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


def get_mofa_list_data(analysis_id, analysis_history_list):
    list_data = []
    for analysis_history in analysis_history_list:
        inference_type = analysis_history.inference_type
        click_url_1 = None

        if inference_type == INFERENCE_MOFA:
            click_url_1 = reverse('explore_data', kwargs={
                'analysis_id': analysis_id,
            })

    item = [analysis_history, click_url_1]
    list_data.append(item)
    return list_data


def get_result_df(df,view, factor):
    df.set_index('feature', inplace=True)
    df.drop(['index', 'factor', 'value_abs', 'view'], axis=1, inplace=True)
    label = 'weight_view%s_factor%s' % (str(view), str(factor))
    df.columns = [label]
    return df


def build_mofapipeline(mofa_filepath):
    m = MofaPipeline()
    m.load_mofa(mofa_filepath)
    m.build_mofa()

    return m

