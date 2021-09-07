import copy

import numpy as np
from loguru import logger

from linker.constants import PKS, PATHWAY_PK, NA


def merge_json_data(json_data, data_type, case, control, result_df):
    new_json_data = copy.deepcopy(json_data)
    res = result_df.to_dict()
    label = '%s_vs_%s' % (case, control)
    padj_label = 'padj_%s' % label
    fc_label = 'FC_%s' % label

    #  remove the previous DE result if exists
    for i in range(len(new_json_data)):
        item = new_json_data[i]
        if padj_label in item:
            del item[padj_label]
            # logger.debug('Removed old padj value')
        if fc_label in item:
            del item[fc_label]
            # logger.debug('Removed old FC value')

    # set new DE result to json_data
    for i in range(len(new_json_data)):
        item = new_json_data[i]
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
    return new_json_data


def update_pathway_analysis_data(json_data, pathway_df):
    new_json_data = copy.deepcopy(json_data)

    # select the columns containing the results ('ending with comb_p')
    result_cols = list(filter(lambda x: x.endswith('comb_p'), pathway_df.columns))
    pals_df = pathway_df[result_cols]

    # remove 'comb_p' from the column names and turn it to dictionary
    pals_df = pals_df.rename(columns={
        col: '_'.join(col.split(' ')[0:-1]).strip() for col in pals_df.columns
    })
    pals_dict = pals_df.to_dict()

    #  remove the previous PALS if exists
    for pathway_dict in new_json_data:
        for comparison in pals_dict:
            key = comparison_to_key(comparison)
            if key in pathway_dict:
                del pathway_dict[key]

    # get pathway analysis data and modify its json_data to include the PALS results
    hits = 0
    for pathway_dict in new_json_data:
        pathway_pk = pathway_dict[PATHWAY_PK]
        found = False
        for comparison in pals_dict:
            key = comparison_to_key(comparison)
            try:
                pals_results = pals_dict[comparison]
                pathway_dict[key] = pals_results[pathway_pk]
                found = True
            except KeyError:  # pathway is not present in dataset, so it isn't included in PALS results
                pathway_dict[key] = NA
        if found:
            hits += 1
    logger.debug('Updated %d pathways' % hits)
    return new_json_data

def merge_json_data_mofa(json_data, data_type, view, factor, result_df):
    new_json_data = copy.deepcopy(json_data)
    res = result_df.to_dict()
    weight_label = 'weight_view%s_factor%s' % (str(view), str(factor))

    #  remove the previous DE result if exists
    for i in range(len(new_json_data)):
        item = new_json_data[i]
        if weight_label in item:
            del item[weight_label]

    # set new DE result to json_data
    for i in range(len(new_json_data)):
        item = new_json_data[i]
        key = item[PKS[data_type]]
        try:
            weight = res['weight_label'][key]
            if np.isnan(weight):
                weight = None
        except KeyError:
            weight = None

        item[weight_label] = weight

    return new_json_data


def comparison_to_key(comparison):
    # remove space and last underscore from the comparison name if comparison ends with '_'
    if comparison.endswith('_'):
        key = comparison.strip().rsplit('_', 1)[0]
    else:
        key = comparison
    # key = 'PLAGE_%s' % key
    return key
