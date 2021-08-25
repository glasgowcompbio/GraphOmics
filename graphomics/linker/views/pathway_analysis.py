import pandas as pd
from loguru import logger
from pals.GSEA import GSEA
from pals.ORA import ORA
from pals.PLAGE import PLAGE
from pals.common import DATABASE_REACTOME_KEGG, DATABASE_REACTOME_CHEBI, DATABASE_REACTOME_UNIPROT, \
    DATABASE_REACTOME_ENSEMBL
from pals.feature_extraction import DataSource

from linker.constants import PKS, COMPOUND_DATABASE_KEGG, COMPOUND_DATABASE_CHEBI, COMPOUNDS, \
    PROTEINS, GENES, MIN_REPLACE_PROTEOMICS_METABOLOMICS, MIN_REPLACE_GENOMICS, PLAGE_NUM_RESAMPLES, \
    PLAGE_RANDOM_SEED
from linker.views.functions import get_group_members, get_standardized_df


def get_pals_data_source(analysis, analysis_data, case, control, min_hits):
    axis = 1
    X_std, data_df, design_df = get_standardized_df(analysis_data, axis, pk_cols=PKS)
    if design_df is None:
        return None

    # if this is a pimp data, the index of X_std will be in this format:
    # <compound_id>_<peak_id>
    # we need to remove the <peak_id> for PALS compound matching to work
    old_index = X_std.index.values
    new_index = []
    for idx in old_index:
        if '_' in idx:
            tokens = idx.split('_')
            new_index.append(tokens[0])
        else:
            new_index.append(idx)
    assert len(old_index) == len(new_index)
    X_std = X_std.rename(index=dict(zip(old_index, new_index)))

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

    # select database name
    database_name, min_replace = _get_database_name(analysis, analysis_data)

    # create a PALS data source
    assert database_name is not None
    ds = DataSource(X_std, annotation_df, experimental_design, database_name,
                    reactome_species, reactome_metabolic_pathway_only, reactome_query, min_replace=min_replace,
                    min_hits=min_hits)

    return ds


def _get_database_name(analysis, analysis_data):
    min_replace = None
    database_name = None
    if analysis_data.data_type == COMPOUNDS:
        if analysis.metadata['compound_database_str'] == COMPOUND_DATABASE_KEGG:
            database_name = DATABASE_REACTOME_KEGG
        elif analysis.metadata['compound_database_str'] == COMPOUND_DATABASE_CHEBI:
            database_name = DATABASE_REACTOME_CHEBI
        min_replace = MIN_REPLACE_PROTEOMICS_METABOLOMICS
    elif analysis_data.data_type == PROTEINS:
        database_name = DATABASE_REACTOME_UNIPROT
        min_replace = MIN_REPLACE_PROTEOMICS_METABOLOMICS
    elif analysis_data.data_type == GENES:
        database_name = DATABASE_REACTOME_ENSEMBL
        min_replace = MIN_REPLACE_GENOMICS
    return database_name, min_replace


def get_comparison(case, control):
    return {
        'case': case.lower(),
        'control': control.lower(),
        'name': '%s_vs_%s' % (case, control)
    }


def run_pals(ds):
    logger.info('Running PALS')
    pals = PLAGE(ds, num_resamples=PLAGE_NUM_RESAMPLES, seed=PLAGE_RANDOM_SEED)
    pathway_df = pals.get_pathway_df(standardize=False)
    return pathway_df


def run_ora(ds):
    logger.info('Running ORA')
    ora = ORA(ds)
    pathway_df = ora.get_pathway_df(standardize=False)
    return pathway_df


def run_gsea(ds):
    logger.info('Running GSEA')
    gsea = GSEA(ds, pbar=True)
    pathway_df = gsea.get_pathway_df(standardize=False)
    return pathway_df


