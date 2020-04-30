import json
from urllib.parse import quote

import pandas as pd
import requests
from django import forms
from django_select2.forms import Select2Widget
from loguru import logger
from sklearn import preprocessing

from linker.constants import PKS, FC_COL_PREFIX, NA, AddNewDataDict, SELECT_WIDGET_ATTRS, PADJ_COL_PREFIX, \
    REACTOME_PVALUE_COLNAME, REACTOME_FOLD_CHANGE_COLNAME
from linker.views.functions import get_last_analysis_data, get_dataframes


def get_omics_data(analysis, data_types, form):
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
    return analysis_data, omics_data


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


def get_used_dtypes(form_data, omics_data):
    used_dtypes = []
    for dtype in omics_data:
        res = omics_data[dtype]
        fieldname = res['fieldname']
        if fieldname in form_data and len(form_data[fieldname]) > 0:
            used_dtypes.append(dtype)
    return used_dtypes


def get_data(form_data, omics_data, used_dtypes, threshold):
    dfs = []
    for dtype in used_dtypes:
        res = omics_data[dtype]
        df = res['df']
        fieldname = res['fieldname']

        colname = form_data[fieldname]
        padj_colname = PADJ_COL_PREFIX + colname
        fc_colname = FC_COL_PREFIX + colname
        df = df[[padj_colname, fc_colname]]
        df = df.rename(columns={
            padj_colname: REACTOME_PVALUE_COLNAME,
            fc_colname: REACTOME_FOLD_CHANGE_COLNAME
        })

        # filter dataframe
        df.dropna(inplace=True)
        df = df[df[REACTOME_PVALUE_COLNAME] > 0]  # exclude NA rows
        df = df[df[REACTOME_PVALUE_COLNAME] <= threshold]  # filter dataframe by p-value threshold
        df = df[REACTOME_FOLD_CHANGE_COLNAME].to_frame()  # convert series to dataframe

        # scale features between (-1, 1) range
        # df = 2 ** df
        scaled_data = preprocessing.power_transform(df[[REACTOME_FOLD_CHANGE_COLNAME]], method='yeo-johnson')
        #scaled_data = preprocessing.minmax_scale(df[REACTOME_FOLD_CHANGE_COLNAME], feature_range=(-1, 1))
        df[REACTOME_FOLD_CHANGE_COLNAME] = scaled_data  # set scaled data back to the dataframe

        dfs.append(df)

    df = pd.concat(dfs)
    return df


def to_ora_tsv(entities):
    data = '#id\n'
    data += '\n'.join(entities)
    return data


def to_expression_tsv(df):
    # convert dataframe to tab-separated values
    # first column in the header has to start with a '#' sign
    # can't use scientific notation, so we format to %.15f
    data = df.to_csv(sep='\t', header=True, index_label='#id', float_format='%.15f')
    return data


def get_analysis_first_species(analysis):
    # get first species of this analysis
    analysis_species = analysis.get_species_list()
    assert len(analysis_species) >= 1
    if len(analysis_species) > 1:
        logger.warning('Multiple species detected. Using only the first species for analysis.')
    encoded_species = quote(analysis_species[0])
    logger.debug('Species: ' + encoded_species)
    return encoded_species


def send_to_reactome(data, encoded_species):
    # refer to https://reactome.org/AnalysisService/#/identifiers/getPostTextUsingPOST
    url = 'https://reactome.org/AnalysisService/identifiers/?interactors=false&species=' + encoded_species + \
          '&sortBy=ENTITIES_PVALUE&order=ASC&resource=TOTAL&pValue=1&includeDisease=true'
    logger.debug('Reactome URL: ' + url)

    # make a POSt request to Reactome Analysis service
    response = requests.post(url, headers={'Content-Type': 'text/plain'}, data=data.encode('utf-8'))
    logger.debug('Response status code = %d' % response.status_code)

    status_code = response.status_code
    if status_code == 200:
        json_response = json.loads(response.text)
    else:
        json_response = None
    return status_code, json_response


def parse_reactome_json(json_response):
    # see https://reactome.org/userguide/analysis for results explanation
    token = json_response['summary']['token']
    pathways = json_response['pathways']

    reactome_url = 'https://reactome.org/PathwayBrowser/#DTAB=AN&ANALYSIS=' + token
    logger.debug('Pathway analysis token: ' + token)
    logger.debug('Pathway analysis URL: ' + reactome_url)

    # https://stackoverflow.com/questions/6027558/flatten-nested-dictionaries-compressing-keys
    pathways_df = pd.io.json.json_normalize(pathways, sep='_')
    return pathways_df, reactome_url, token


def get_first_colname(form_data, omics_data, used_dtypes):
    first_dtype = used_dtypes[0]
    res = omics_data[first_dtype]
    fieldname = res['fieldname']
    first_colname = form_data[fieldname]
    return first_colname
