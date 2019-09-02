import json

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from django.http import JsonResponse
from django.utils import timezone

from linker.constants import *
from linker.models import Analysis, AnalysisGroup
from linker.views.functions import get_last_data, get_dataframes, fig_to_div
from linker.views.gene_ontologies import GOAnalysis
from linker.views.gene_ontologies_utils import GO_NAMESPACES


def list_groups(request, analysis_id):
    analysis = Analysis.objects.get(id=analysis_id)
    analysis_groups = AnalysisGroup.objects.filter(analysis=analysis).order_by('-timestamp')
    data = {'list': []}
    for g in analysis_groups:
        label = g.display_name
        value = g.id
        data['list'].append({'label': label, 'value': value})
    return JsonResponse(data)


def save_group(request, analysis_id):
    analysis = Analysis.objects.get(id=analysis_id)
    group_name = request.POST.get('groupName')
    group_desc = request.POST.get('groupDesc')
    linker_state = request.POST.get('state')

    group = AnalysisGroup.objects.create(
        analysis=analysis,
        display_name=group_name,
        description=group_desc,
        linker_state=linker_state,
        timestamp=timezone.localtime()
    )
    group.save()

    data = {'success': True}
    return JsonResponse(data)


def load_group(request, analysis_id):
    analysis = Analysis.objects.get(id=analysis_id)
    group_id = int(request.GET['groupId'])
    group = AnalysisGroup.objects.get(id=group_id)
    linker_state = group.linker_state
    data = {
        'groupId': group.id,
        'groupName': group.display_name,
        'groupDesc': group.description,
        'state': linker_state,
        'timestamp': group.timestamp
    }
    return JsonResponse(data)


def get_boxplot(request, analysis_id):
    analysis = Analysis.objects.get(id=analysis_id)
    data_type = int(request.POST['dataType'])
    assert data_type in [GENOMICS, PROTEOMICS, METABOLOMICS]

    last_query_result = get_last_query_result(request)
    analysis_data = get_last_data(analysis, data_type)
    data_df, design_df = get_dataframes(analysis_data, pk_cols=IDS)
    if design_df is None:  # no data
        x, y_df = None, None
    else:
        # create selected data and design dataframes
        x, y_df = get_plotly_data(design_df, last_query_result, data_type)

    # make plotly figure and render as div
    fig = get_plotly_boxplot(x, y_df)
    div = fig_to_div(fig)
    data = {'div': div}
    return JsonResponse(data)


def get_last_query_result(request):
    try:
        # try to retrieve last query result from database
        group_id = int(request.POST['groupId'])
        group = AnalysisGroup.objects.get(id=group_id)
        linker_state = json.loads(group.linker_state)
        last_query_result = linker_state['lastQueryResult']
    except ValueError:  # no group id has been provided
        last_query_result = json.loads(
            request.POST['lastQueryResult'])  # retrieve the lastQueryResult directly from the request
    return last_query_result


def get_plotly_data(design_df, last_query_result, data_type):
    selection_df = get_selection_df(data_type, last_query_result)

    # construct x for boxplot
    x = design_df[GROUP_COL].values

    # construct y for boxplot
    y = np.log2(selection_df[design_df.index])
    return x, y


def get_selection_df(data_type, last_query_result):
    table_name = TABLE_IDS[data_type]
    id_col = IDS[data_type]
    selection_df = pd.DataFrame(last_query_result[table_name]).set_index(id_col)
    try:
        selection_df = selection_df.drop(labels=NA)
    except KeyError:
        pass  # do nothing
    return selection_df


def get_plotly_boxplot(x, y_df):
    fig = go.Figure()
    if y_df is not None:
        for idx, row in y_df.iterrows():
            # skip if all nans since nothing is observed
            if np.isnan(row.values).all():
                continue
            fig.add_trace(go.Box(
                y=row.values,
                x=x,
                name=idx,
            ))

    fig.update_layout(
        yaxis_title='log2(measurement)',
        boxmode='group'  # group together boxes of the different traces for each value of x
    )
    return fig


def get_gene_ontology(request, analysis_id):
    analysis = Analysis.objects.get(id=analysis_id)
    data_type = GENOMICS
    namespace = request.POST['namespace']
    assert namespace in GO_NAMESPACES

    # TODO: can't remember why we support multiple species list per experiment ...
    try:
        first_species = analysis.get_species_list()[0] # take the first one always

        # get the list of selected gene names
        last_query_result = get_last_query_result(request)
        selection_df = get_selection_df(data_type, last_query_result)
        selection_names = selection_df.index.values

        # get the list of background gene names
        analysis_data = get_last_data(analysis, data_type)
        data_df, design_df = get_dataframes(analysis_data, pk_cols=IDS)
        background_gene_names = data_df.index.values

        # create gene ontology analysis
        goa = GOAnalysis(first_species, namespace, background_gene_names)
        df = goa.goea_analysis_df(selection_names)
        html_data = df.to_html()

    except KeyError: # can't find the mapping between species name to GO filename to download
        html_data = '<p>Gene ontology analysis not available</p>'

    data = {'div': html_data}
    return JsonResponse(data)