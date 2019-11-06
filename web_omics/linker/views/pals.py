import pandas as pd

from linker.constants import PKS, COMPOUND_DATABASE_KEGG, COMPOUND_DATABASE_CHEBI, PATHWAY_PK, NA
from linker.views.functions import get_group_members, get_standardized_df
from pals.common import DATABASE_REACTOME_KEGG, DATABASE_REACTOME_CHEBI
from pals.feature_extraction import DataSource
from pals.pathway_analysis import PALS


def get_pals_data_source(analysis, analysis_data):
    axis = 1
    X_std, data_df, design_df = get_standardized_df(analysis_data, axis, pk_cols=PKS)
    if design_df is None:
        return None

    # retrieve experimental design information
    experimental_design = {
        'comparisons': [],
        'groups': get_group_members(analysis_data)
    }

    # populate comparison values in the experimental design
    comparison_cols = list(filter(lambda x: x.lower().startswith('padj_'), data_df.columns))
    for comparison_col in comparison_cols:
        tokens = comparison_col.split('_')
        comparison_case = tokens[1]
        comparison_control = tokens[3]
        experimental_design['comparisons'].append({
            'case': comparison_case,
            'control': comparison_control,
            'name': '%s_vs_%s' % (comparison_case, comparison_control)
        })

    assert len(experimental_design['comparisons']) > 0

    # retrieve annotation df
    formula_df = pd.DataFrame()
    formula_df['entity_id'] = X_std.index
    formula_df.index.name = 'row_id'
    formula_df.head()

    # retrieve measurement df
    X_std.reset_index(drop=True, inplace=True)
    X_std.index.name = 'row_id'
    X_std.head()

    # create PALS data source
    database_name = None
    if analysis.metadata['compound_database_str'] == COMPOUND_DATABASE_KEGG:
        database_name = DATABASE_REACTOME_KEGG
    elif analysis.metadata['compound_database_str'] == COMPOUND_DATABASE_CHEBI:
        database_name = DATABASE_REACTOME_CHEBI
    reactome_metabolic_pathway_only = analysis.metadata['metabolic_pathway_only']
    reactome_species = analysis.metadata['species_list'][0]  # assume the first one
    reactome_query = True
    ds = DataSource(X_std, formula_df, experimental_design, database_name,
                    reactome_species, reactome_metabolic_pathway_only, reactome_query)
    return ds


def run_pals(ds):
    pals = PALS(ds)
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

    # get pathway analysis data and modify its json_data to include the PALS results
    new_json_data = analysis_data.json_data
    for pathway_dict in new_json_data:
        pathway_pk = pathway_dict[PATHWAY_PK]
        for comparison in pals_dict:
            pals_results = pals_dict[comparison]
            # remove space and last underscore from the comparison name
            key = comparison.strip().rsplit('_', 1)[0]
            # key = 'PALS_%s' % key
            if key not in pathway_dict:
                try:
                    pathway_dict[key] = pals_results[pathway_pk]
                except KeyError:  # pathway is not present in dataset, so it isn't included in PALS results
                    pathway_dict[key] = NA
    return new_json_data
