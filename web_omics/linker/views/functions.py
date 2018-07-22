import json
from io import StringIO

import collections
import pandas as pd

from django.templatetags.static import static
from django.conf import settings
import urllib.request
import pickle

from linker.models import Analysis, AnalysisData
from linker.reactome import get_reaction_df
from linker.constants import GENOMICS, PROTEOMICS, METABOLOMICS, REACTIONS, PATHWAYS, GENES_TO_PROTEINS, \
    PROTEINS_TO_REACTIONS, COMPOUNDS_TO_REACTIONS, REACTIONS_TO_PATHWAYS
from linker.metadata import kegg_to_chebi, get_gene_names, get_compound_metadata, clean_label
from linker.reactome import ensembl_to_uniprot, uniprot_to_reaction, compound_to_reaction, \
    reaction_to_metabolite_pathway, reaction_to_uniprot, reaction_to_compound, uniprot_to_ensembl

Relation = collections.namedtuple('Relation', 'keys values mapping_list')
NA = '-'  # this should be something that will appear first in the table when sorted alphabetically

GENE_PK = 'gene_pk'
PROTEIN_PK = 'protein_pk'
COMPOUND_PK = 'compound_pk'
REACTION_PK = 'reaction_pk'
PATHWAY_PK = 'pathway_pk'

# COMPOUND_DATABASE = 'ChEBI'
COMPOUND_DATABASE = 'KEGG'

def reactome_mapping(request, genes_str, proteins_str, compounds_str, species_list):
    ### all the ids that we have from the user ###
    observed_gene_df, group_gene_df, observed_gene_ids = csv_to_dataframe(genes_str)
    observed_protein_df, group_protein_df, observed_protein_ids = csv_to_dataframe(proteins_str)
    observed_compound_df, group_compound_df, observed_compound_ids = csv_to_dataframe(compounds_str)

    # try to convert all kegg ids to chebi ids, if possible
    print('Converting kegg ids -> chebi ids')
    observed_compound_ids = get_ids_from_dataframe(observed_compound_df)
    rel_path = static('data/kegg_to_chebi.p')
    pickled_url = request.build_absolute_uri(rel_path)
    kegg_2_chebi = {}
    with urllib.request.urlopen(pickled_url) as url:
        kegg_2_chebi = pickle.load(url)
    for cid in observed_compound_ids:
        if cid not in kegg_2_chebi:
            print('Not found: %s' % cid)
            kegg_2_chebi[cid] = cid

    if observed_compound_df is not None:
        if COMPOUND_DATABASE == 'ChEBI':
            observed_compound_df.iloc[:, 0] = observed_compound_df.iloc[:, 0].map(
                kegg_2_chebi)  # assume 1st column is id
        observed_compound_ids = get_ids_from_dataframe(observed_compound_df)

    ### map genes -> proteins ###
    print('Mapping genes -> proteins')
    gene_2_proteins_mapping, _ = ensembl_to_uniprot(observed_gene_ids, species_list)
    gene_2_proteins = make_relations(gene_2_proteins_mapping, GENE_PK, PROTEIN_PK, value_key=None)

    ### maps proteins -> reactions ###
    print('Mapping proteins -> reactions')
    protein_ids_from_genes = gene_2_proteins.values
    known_protein_ids = list(set(observed_protein_ids + protein_ids_from_genes))
    protein_2_reactions_mapping, _ = uniprot_to_reaction(known_protein_ids, species_list)
    protein_2_reactions = make_relations(protein_2_reactions_mapping, PROTEIN_PK, REACTION_PK,
                                         value_key='reaction_id')

    ### maps compounds -> reactions ###
    print('Mapping compounds -> reactions')
    compound_2_reactions_mapping, _ = compound_to_reaction(observed_compound_ids, species_list)
    compound_2_reactions = make_relations(compound_2_reactions_mapping, COMPOUND_PK, REACTION_PK,
                                          value_key='reaction_id')

    ### maps reactions -> metabolite pathways ###
    print('Mapping reactions -> metabolite pathways')
    reaction_ids_from_proteins = protein_2_reactions.values
    reaction_ids_from_compounds = compound_2_reactions.values
    reaction_ids = list(set(reaction_ids_from_proteins + reaction_ids_from_compounds))
    reaction_2_pathways_mapping, reaction_2_pathways_id_to_names = reaction_to_metabolite_pathway(reaction_ids,
                                                                                                  species_list)
    reaction_2_pathways = make_relations(reaction_2_pathways_mapping, REACTION_PK, PATHWAY_PK,
                                         value_key='pathway_id')
    reaction_ids = reaction_2_pathways.keys  # keep only reactions in metabolic pathways

    ### maps reactions -> proteins ###
    print('Mapping reactions -> proteins')
    mapping, _ = reaction_to_uniprot(reaction_ids, species_list)
    reaction_2_proteins = make_relations(mapping, REACTION_PK, PROTEIN_PK, value_key=None)
    protein_2_reactions = reverse_relation(reaction_2_proteins)
    all_protein_ids = protein_2_reactions.keys

    ### maps reactions -> compounds ###
    print('Mapping reactions -> compounds')
    reaction_2_compounds_mapping, reaction_to_compound_id_to_names = reaction_to_compound(reaction_ids, species_list)
    reaction_2_compounds = make_relations(reaction_2_compounds_mapping, REACTION_PK, COMPOUND_PK, value_key=None)
    compound_2_reactions = reverse_relation(reaction_2_compounds)
    all_compound_ids = compound_2_reactions.keys

    ### map proteins -> genes ###
    print('Mapping proteins -> genes')
    mapping, _ = uniprot_to_ensembl(all_protein_ids, species_list)
    protein_2_genes = make_relations(mapping, PROTEIN_PK, GENE_PK, value_key=None)
    gene_2_proteins = merge_relation(gene_2_proteins, reverse_relation(protein_2_genes))
    inferred_gene_ids = protein_2_genes.values
    all_gene_ids = list(set(observed_gene_ids + inferred_gene_ids))

    ### add links ###

    # map NA to NA
    gene_2_proteins = add_links(gene_2_proteins, GENE_PK, PROTEIN_PK, [NA], [NA])
    protein_2_reactions = add_links(protein_2_reactions, PROTEIN_PK, REACTION_PK, [NA], [NA])
    compound_2_reactions = add_links(compound_2_reactions, COMPOUND_PK, REACTION_PK, [NA], [NA])
    reaction_2_pathways = add_links(reaction_2_pathways, REACTION_PK, PATHWAY_PK, [NA], [NA])

    # map genes that have no proteins to NA
    gene_pk_list = [x for x in all_gene_ids if x not in gene_2_proteins.keys]
    gene_2_proteins = add_links(gene_2_proteins, GENE_PK, PROTEIN_PK, gene_pk_list, [NA])

    # map proteins that have no genes to NA
    protein_pk_list = [x for x in all_protein_ids if x not in gene_2_proteins.values]
    gene_2_proteins = add_links(gene_2_proteins, GENE_PK, PROTEIN_PK, [NA], protein_pk_list)

    # map proteins that have no reactions to NA
    protein_pk_list = [x for x in all_protein_ids if x not in protein_2_reactions.keys]
    protein_2_reactions = add_links(protein_2_reactions, PROTEIN_PK, REACTION_PK, protein_pk_list, [NA])

    # map reactions that have no proteins to NA
    reaction_pk_list = [x for x in reaction_ids if x not in protein_2_reactions.values]
    protein_2_reactions = add_links(protein_2_reactions, PROTEIN_PK, REACTION_PK, [NA], reaction_pk_list)

    # map compounds that have no reactions to NA
    compound_pk_list = [x for x in all_compound_ids if x not in compound_2_reactions.keys]
    compound_2_reactions = add_links(compound_2_reactions, COMPOUND_PK, REACTION_PK, compound_pk_list, [NA])

    # map reactions that have no compounds to NA
    reaction_pk_list = [x for x in reaction_ids if x not in compound_2_reactions.values]
    compound_2_reactions = add_links(compound_2_reactions, COMPOUND_PK, REACTION_PK, [NA], reaction_pk_list)

    # map reactions that have no pathways to NA
    reaction_pk_list = [x for x in reaction_ids if x not in reaction_2_pathways.keys]
    reaction_2_pathways = add_links(reaction_2_pathways, REACTION_PK, PATHWAY_PK, reaction_pk_list, [NA])

    gene_2_proteins_json = json.dumps(gene_2_proteins.mapping_list)
    protein_2_reactions_json = json.dumps(protein_2_reactions.mapping_list)
    compound_2_reactions_json = json.dumps(compound_2_reactions.mapping_list)
    reaction_2_pathways_json = json.dumps(reaction_2_pathways.mapping_list)

    rel_path = static('data/gene_names.p')
    pickled_url = request.build_absolute_uri(rel_path)
    metadata_map = get_gene_names(all_gene_ids, pickled_url)
    genes_json = pk_to_json(GENE_PK, 'gene_id', all_gene_ids, metadata_map, observed_gene_df, observed_ids=observed_gene_ids)

    # metadata_map = get_uniprot_metadata_online(uniprot_ids)
    proteins_json = pk_to_json('protein_pk', 'protein_id', all_protein_ids, metadata_map, observed_protein_df, observed_ids=observed_protein_ids)

    rel_path = static('data/compound_names.json')
    json_url = request.build_absolute_uri(rel_path)
    metadata_map = get_compound_metadata(all_compound_ids, json_url, reaction_to_compound_id_to_names)
    compounds_json = pk_to_json('compound_pk', 'compound_id', all_compound_ids, metadata_map, observed_compound_df, observed_ids=observed_compound_ids)

    metadata_map = {}
    for name in reaction_2_pathways_id_to_names:
        tok = reaction_2_pathways_id_to_names[name]['name']
        filtered = clean_label(tok)
        species = reaction_2_pathways_id_to_names[name]['species']
        metadata_map[name] = {'display_name': filtered, 'species': species}

    # print('Computing reaction and pathway counts')
    # reaction_count_df, pathway_count_df = get_count_df(gene_2_proteins_mapping, protein_2_reactions_mapping,
    #                                                    compound_2_reactions_mapping, reaction_2_pathways_mapping,
    #                                                    species_list)
    reaction_count_df = None
    pathway_count_df = None

    pathway_ids = reaction_2_pathways.values
    reactions_json = pk_to_json('reaction_pk', 'reaction_id', reaction_ids, metadata_map, reaction_count_df, has_species=True)
    pathways_json = pk_to_json('pathway_pk', 'pathway_id', pathway_ids, metadata_map, pathway_count_df, has_species=True)

    results = {
        GENOMICS: genes_json,
        PROTEOMICS: proteins_json,
        METABOLOMICS: compounds_json,
        REACTIONS: reactions_json,
        PATHWAYS: pathways_json,
        GENES_TO_PROTEINS: gene_2_proteins_json,
        PROTEINS_TO_REACTIONS: protein_2_reactions_json,
        COMPOUNDS_TO_REACTIONS: compound_2_reactions_json,
        REACTIONS_TO_PATHWAYS: reaction_2_pathways_json,
        'group_gene_df': group_gene_df,
        'group_protein_df': group_protein_df,
        'group_compound_df': group_compound_df
    }
    return results


def save_analysis(analysis_name, analysis_desc,
                  genes_str, proteins_str, compounds_str,
                  results, species_list, current_user):
    metadata = {
        'genes_str': genes_str,
        'proteins_str': proteins_str,
        'compounds_str': compounds_str,
        'species_list': species_list
    }
    analysis = Analysis.objects.create(name=analysis_name,
                                       description=analysis_desc,
                                       metadata=metadata,
                                       user=current_user)
    print('Saved analysis', analysis.pk, '(', species_list, ')')
    datatype_json = {
        GENOMICS: (results[GENOMICS], 'genes_json', results['group_gene_df']),
        PROTEOMICS: (results[PROTEOMICS], 'proteins_json', results['group_protein_df']),
        METABOLOMICS: (results[METABOLOMICS], 'compounds_json', results['group_compound_df']),
        REACTIONS: (results[REACTIONS], 'reactions_json', None),
        PATHWAYS: (results[PATHWAYS], 'pathways_json', None),
        GENES_TO_PROTEINS: (results[GENES_TO_PROTEINS], 'gene_proteins_json', None),
        PROTEINS_TO_REACTIONS: (results[PROTEINS_TO_REACTIONS], 'protein_reactions_json', None),
        COMPOUNDS_TO_REACTIONS: (results[COMPOUNDS_TO_REACTIONS], 'compound_reactions_json', None),
        REACTIONS_TO_PATHWAYS: (results[REACTIONS_TO_PATHWAYS], 'reaction_pathways_json', None),
    }
    data = {}
    for k, v in datatype_json.items():

        # v is a tuple defined in the datatype_json dictionary above
        json_str, ui_label, group_info = v
        data[ui_label] = json_str

        json_design = group_info.to_json() if group_info is not None else None
        analysis_data = AnalysisData(analysis=analysis,
                                     json_data=json.loads(json_str), json_design=json_design, data_type=k)
        analysis_data.save()
        print('Saved analysis data', analysis_data.pk, 'for analysis', analysis.pk)

        # if settings.DEBUG:
        #     save_json_string(v[0], 'static/data/debugging/' + v[1] + '.json')
    print()
    return analysis, data


def get_count_df(gene_2_proteins_mapping, protein_2_reactions_mapping, compound_2_reactions_mapping,
                 reaction_2_pathways_mapping, species_list):
    count_df, pathway_compound_counts, pathway_protein_counts = get_reaction_df(
        gene_2_proteins_mapping,
        protein_2_reactions_mapping,
        compound_2_reactions_mapping,
        reaction_2_pathways_mapping,
        species_list)

    reaction_count_df = count_df.rename({
        'reaction_id': 'reaction_pk',
        'observed_protein_count': 'R_E',
        'observed_compound_count': 'R_C'
    }, axis='columns')

    reaction_count_df = reaction_count_df.drop([
        'reaction_name',
        'protein_coverage',
        'compound_coverage',
        'all_coverage',
        'protein',
        'all_protein_count',
        'compound',
        'all_compound_count',
        'pathway_ids',
        'pathway_names'
    ], axis=1)

    pathway_pks = set(list(pathway_compound_counts.keys()) + list(pathway_protein_counts.keys()))
    data = []
    for pathway_pk in pathway_pks:
        try:
            p_e = pathway_protein_counts[pathway_pk]
        except KeyError:
            p_e = 0
        try:
            p_c = pathway_compound_counts[pathway_pk]
        except KeyError:
            p_c = 0
        data.append((pathway_pk, p_e, p_c))
    pathway_count_df = pd.DataFrame(data, columns=['pathway_pk', 'P_E', 'P_C'])

    return reaction_count_df, pathway_count_df


def save_json_string(data, outfile):
    with open(outfile, 'w') as f:
        f.write(data)
        print('Saving', outfile)


def csv_to_dataframe(csv_str):
    # extract group, if any
    filtered_str = ''
    group_str = None
    for line in csv_str.splitlines():
        if line.startswith('group'):
            group_str = line
        else:
            filtered_str += line + '\n'

    # extract id values
    data = StringIO(filtered_str)
    try:
        data_df = pd.read_csv(data)
        data_df.iloc[:, 0] = data_df.iloc[:, 0].astype(str) # assume id is in the first column and is a string
        id_list = data_df.iloc[:, 0].values.tolist()
    except pd.errors.EmptyDataError:
        data_df = None
        id_list = []

    # create grouping dataframe
    group_df = None
    if data_df is not None:
        sample_data = data_df.columns.values
        if group_str is not None:
            print(group_str)
            group_data = group_str.split(',')
            group_df = pd.DataFrame(list(zip(sample_data[1:], group_data[1:])), columns=['sample', 'group'])
        else:
            group_df = pd.DataFrame(sample_data[1:], columns=['sample'])

    return data_df, group_df, id_list


def get_ids_from_dataframe(df):
    if df is None:
        return []
    else:
        return df.iloc[:, 0].values.tolist() # id is always the first column


def merge_relation(r1, r2):
    unique_keys = list(set(r1.keys + r2.keys))
    unique_values = list(set(r1.values + r2.values))
    mapping_list = r1.mapping_list + r2.mapping_list
    mapping_list = list(map(dict, set(map(lambda x: frozenset(x.items()), mapping_list))))  # removes duplicates, if any
    return Relation(keys=list(unique_keys), values=list(unique_values),
                    mapping_list=mapping_list)


def reverse_relation(rel):
    return Relation(keys=rel.values, values=rel.keys, mapping_list=rel.mapping_list)


def pk_to_json(pk_label, display_label, data, metadata_map, observed_df, has_species=False, observed_ids=None):
    # turn the first column of the dataframe into index
    if observed_df is not None:
        observed_df = observed_df.set_index(observed_df.columns[0])
        observed_df = observed_df[~observed_df.index.duplicated(keep='first')]  # remove row with duplicate indices
        observed_df = observed_df.fillna(value=0)  # replace all NaNs with 0s

    output = []
    for item in sorted(data):

        if item == NA:
            continue  # handled below after this loop

        # add observed status and the primary key label to row data
        observed = False
        if observed_ids and item in observed_ids:
            observed = True
        row = {'obs': observed, pk_label: item}

        # add display label to row_data
        if len(metadata_map) > 0 and item in metadata_map and metadata_map[item] is not None:
            label = metadata_map[item]['display_name']
            # get the species if it's there too
            if has_species and 'species' in metadata_map[item]:
                species = metadata_map[item]['species']
        else:
            label = item  # otherwise use the item id as the label
        row[display_label] = label

        # add the remaining data columns to row
        if observed_df is not None:
            try:
                observed_values = observed_df.loc[item].to_dict()
            except KeyError:  # missing data
                observed_values = {}
                for col in observed_df.columns:
                    observed_values.update({col: 0})
            row.update(observed_values)

        if has_species:
            row['species'] = species

        if row not in output:
            output.append(row)

    # add dummy entry
    row = {'obs': NA, pk_label: NA, display_label: NA}
    if has_species:
        row['species'] = NA

    if observed_df is not None:  # also add the remaining columns
        for col in observed_df.columns:
            row.update({col: 0})

    if row not in output:
        output.append(row)

    output_json = json.dumps(output)
    return output_json


def make_relations(mapping, source_pk, target_pk, value_key=None):
    id_values = []
    mapping_list = []

    for key in mapping:
        value_list = mapping[key]

        # value_list can be either a list of strings or dictionaries
        # check if the first element is a dict, else assume it's a string
        assert len(value_list) > 0
        is_string = True
        first = value_list[0]
        if isinstance(first, dict):
            is_string = False

        # process each element in value_list
        for value in value_list:
            if is_string:  # value_list is a list of string
                actual_value = value
            else:  # value_list is a list of dicts
                assert value_key is not None, 'value_key is missing'
                actual_value = value[value_key]
            id_values.append(actual_value)
            row = {source_pk: key, target_pk: actual_value}
            mapping_list.append(row)

    unique_keys = set(mapping.keys())
    unique_values = set(id_values)

    return Relation(keys=list(unique_keys), values=list(unique_values),
                    mapping_list=mapping_list)


def add_dummy(relation, source_ids, target_ids, source_pk_label, target_pk_label):
    to_add = [x for x in source_ids if x not in relation.keys]
    relation = add_links(relation, source_pk_label, target_pk_label, to_add, [NA])

    # to_add = [x for x in target_ids if x not in relation.values]
    # relation = add_links(relation, source_pk_label, target_pk_label, [NA], to_add)

    # relation = add_links(relation, source_pk_label, target_pk_label, [NA], [NA])
    return relation


def add_links(relation, source_pk_label, target_pk_label, source_pk_list, target_pk_list):
    rel_mapping_list = list(relation.mapping_list)
    rel_keys = relation.keys
    rel_values = relation.values

    for s1 in source_pk_list:
        if s1 not in rel_keys: rel_keys.append(s1)
        for s2 in target_pk_list:
            rel_mapping_list.append({source_pk_label: s1, target_pk_label: s2})
            if s2 not in rel_keys: rel_values.append(s2)

    return Relation(keys=rel_keys, values=rel_values, mapping_list=rel_mapping_list)
