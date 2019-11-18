import pandas as pd
from loguru import logger
from pals.common import DATABASE_REACTOME_KEGG, DATABASE_REACTOME_CHEBI, DATABASE_REACTOME_UNIPROT, \
    DATABASE_REACTOME_ENSEMBL
from pals.feature_extraction import DataSource
from pals.pathway_analysis import PALS

from linker.constants import PKS, COMPOUND_DATABASE_KEGG, COMPOUND_DATABASE_CHEBI, PATHWAY_PK, NA, METABOLOMICS, \
    PROTEOMICS, GENOMICS
from linker.views.functions import get_group_members, get_standardized_df


def get_pals_data_source(analysis, analysis_data, case, control):
    axis = 1
    X_std, data_df, design_df = get_standardized_df(analysis_data, axis, pk_cols=PKS)
    if design_df is None:
        return None

    # retrieve experimental design information
    experimental_design = {
        'comparisons': [get_comparison(case, control)],
        'groups': get_group_members(analysis_data)
    }

    # retrieve annotation df
    annotation_df = pd.DataFrame()
    annotation_df['entity_id'] = X_std.index
    annotation_df.index.name = 'row_id'
    annotation_df.head()

    # retrieve measurement df
    X_std.reset_index(drop=True, inplace=True)
    X_std.index.name = 'row_id'
    X_std.head()

    # create PALS data source
    reactome_metabolic_pathway_only = analysis.metadata['metabolic_pathway_only']
    reactome_species = analysis.metadata['species_list'][0]  # assume the first one
    reactome_query = True
    database_name = None

    # select database name
    if analysis_data.data_type == METABOLOMICS:
        if analysis.metadata['compound_database_str'] == COMPOUND_DATABASE_KEGG:
            database_name = DATABASE_REACTOME_KEGG
        elif analysis.metadata['compound_database_str'] == COMPOUND_DATABASE_CHEBI:
            database_name = DATABASE_REACTOME_CHEBI
    elif analysis_data.data_type == PROTEOMICS:
        database_name = DATABASE_REACTOME_UNIPROT
    elif analysis_data.data_type == GENOMICS:
        database_name = DATABASE_REACTOME_ENSEMBL

    # create a PALS data source
    assert database_name is not None
    ds = DataSource(X_std, annotation_df, experimental_design, database_name,
                    reactome_species, reactome_metabolic_pathway_only, reactome_query)

    return ds


def get_comparison(case, control):
    return {
        'case': case.lower(),
        'control': control.lower(),
        'name': '%s_vs_%s' % (case, control)
    }


def run_pals(ds, plage_weight, hg_weight):
    logger.info('Running PALS with plage_weight=%d hg_weight=%d' % (plage_weight, hg_weight))
    pals = PALS(ds, plage_weight=plage_weight, hg_weight=hg_weight)
    pathway_df = pals.get_pathway_df(standardize=False)
    return pathway_df


def update_pathway_analysis_data(analysis_data, pathway_df):
    # select the columns containing the results ('ending with comb_p')
    result_cols = list(filter(lambda x: x.endswith('comb_p'), pathway_df.columns))
    pals_df = pathway_df[result_cols]

    # remove 'comb_p' from the column names and turn it to dictionary
    pals_df = pals_df.rename(columns={
        col: '_'.join(col.split(' ')[0:-1]).strip() for col in pals_df.columns
    })
    pals_dict = pals_df.to_dict()
    new_json_data = analysis_data.json_data

    #  remove the previous PALS if exists
    for pathway_dict in new_json_data:
        for comparison in pals_dict:
            key = comparison_to_key(comparison)
            if key in pathway_dict:
                del pathway_dict[key]

    # get pathway analysis data and modify its json_data to include the PALS results
    for pathway_dict in new_json_data:
        pathway_pk = pathway_dict[PATHWAY_PK]
        for comparison in pals_dict:
            key = comparison_to_key(comparison)
            try:
                pals_results = pals_dict[comparison]
                pathway_dict[key] = pals_results[pathway_pk]
            except KeyError:  # pathway is not present in dataset, so it isn't included in PALS results
                pathway_dict[key] = NA
    return new_json_data


def comparison_to_key(comparison):
    # remove space and last underscore from the comparison name if comparison ends with '_'
    if comparison.endswith('_'):
        key = comparison.strip().rsplit('_', 1)[0]
    else:
        key = comparison
    # key = 'PALS_%s' % key
    return key
