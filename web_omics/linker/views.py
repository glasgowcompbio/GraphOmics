import json
import re
import urllib.request
from urllib.parse import urlparse
from io import StringIO
import collections

import pandas as pd
import numpy as np

from django.http import HttpResponse
from django.http import JsonResponse
from django.shortcuts import render
from django.templatetags.static import static
from django.views.generic.edit import FormView

from linker.forms import LinkerForm
from linker.metadata import get_compound_metadata_from_json
from linker.metadata import get_single_ensembl_metadata_online, get_single_uniprot_metadata_online, \
    get_single_compound_metadata_online, clean_label, get_gene_names
from linker.reactome import compound_to_reaction, reaction_to_metabolite_pathway, get_reaction_entities
from linker.reactome import ensembl_to_uniprot, uniprot_to_reaction, get_species_dict

Relation = collections.namedtuple('Relation', 'keys values mapping_list')
NA = '-'  # this should be something that will appear first in the table when sorted alphabetically

TRUNCATE_LIMIT = 200

GENE_PK = 'gene_pk'
PROTEIN_PK = 'protein_pk'
COMPOUND_PK = 'compound_pk'
REACTION_PK = 'reaction_pk'
PATHWAY_PK = 'pathway_pk'


class LinkerView(FormView):
    template_name = 'linker/linker.html'
    form_class = LinkerForm
    success_url = 'linker/analysis.html'

    def form_valid(self, form):
        genes_str = form.cleaned_data['genes']
        proteins_str = form.cleaned_data['proteins']
        compounds_str = form.cleaned_data['compounds']
        species_key = int(form.cleaned_data['species'])
        species_dict = get_species_dict()
        species = species_dict[species_key]

        ### all the ids that we have from the user ###
        observed_gene_df = csv_to_dataframe(genes_str)
        observed_protein_df = csv_to_dataframe(proteins_str)
        observed_compound_df = csv_to_dataframe(compounds_str)
        observed_gene_ids = get_ids_from_dataframe(observed_gene_df)
        observed_protein_ids = get_ids_from_dataframe(observed_protein_df)
        observed_compound_ids = get_ids_from_dataframe(observed_compound_df)

        ### map genes -> proteins using Reactome ###

        gene_ids = observed_gene_ids
        mapping, id_to_names = ensembl_to_uniprot(gene_ids, species)
        gene_2_proteins = _make_relations(mapping, GENE_PK, PROTEIN_PK, value_key=None)

        ### maps proteins -> reactions using Reactome ###

        inferred_protein_ids = gene_2_proteins.values
        protein_ids = observed_protein_ids + inferred_protein_ids
        protein_ids = list(set(observed_protein_ids + inferred_protein_ids))
        mapping, id_to_names = uniprot_to_reaction(protein_ids, species)
        protein_2_reactions = _make_relations(mapping, PROTEIN_PK, REACTION_PK, value_key='reaction_id')

        ### maps compounds -> reactions using Reactome ###

        compound_ids = observed_compound_ids
        mapping, id_to_names = compound_to_reaction(compound_ids, species)
        compound_2_reactions = _make_relations(mapping, COMPOUND_PK, REACTION_PK, value_key='reaction_id')

        ### maps reactions -> pathways using Reactome ###

        reaction_ids = list(set(protein_2_reactions.values + compound_2_reactions.values))
        mapping, id_to_names = reaction_to_metabolite_pathway(reaction_ids, species)
        reaction_2_pathways = _make_relations(mapping, REACTION_PK, PATHWAY_PK, value_key='pathway_id')

        ### add links ###

        # map NA to NA
        gene_2_proteins = _add_links(gene_2_proteins, GENE_PK, PROTEIN_PK, [NA], [NA])
        protein_2_reactions = _add_links(protein_2_reactions, PROTEIN_PK, REACTION_PK, [NA], [NA])
        compound_2_reactions = _add_links(compound_2_reactions, COMPOUND_PK, REACTION_PK, [NA], [NA])
        reaction_2_pathways = _add_links(reaction_2_pathways, REACTION_PK, PATHWAY_PK, [NA], [NA])

        # map genes that have no proteins to NA
        gene_pk_list = [x for x in gene_ids if x not in gene_2_proteins.keys]
        gene_2_proteins = _add_links(gene_2_proteins, GENE_PK, PROTEIN_PK, gene_pk_list, [NA])

        # map proteins that have no reactions to NA
        protein_pk_list = [x for x in protein_ids if x not in protein_2_reactions.keys]
        protein_2_reactions = _add_links(protein_2_reactions, PROTEIN_PK, REACTION_PK, protein_pk_list, [NA])

        # map reactions that have no proteins to NA
        reaction_pk_list = [x for x in reaction_ids if x not in compound_2_reactions.values]
        protein_2_reactions = _add_links(protein_2_reactions, COMPOUND_PK, REACTION_PK, reaction_pk_list, [NA])

        # map compounds that have no reactions to NA
        compound_pk_list = [x for x in compound_ids if x not in compound_2_reactions.keys]
        compound_2_reactions = _add_links(compound_2_reactions, COMPOUND_PK, REACTION_PK, compound_pk_list, [NA])

        # map reactions that have no compounds to NA
        reaction_pk_list = [x for x in reaction_ids if x not in compound_2_reactions.values]
        compound_2_reactions = _add_links(compound_2_reactions, COMPOUND_PK, REACTION_PK, [NA], reaction_pk_list)

        # map reactions that have no pathways to NA
        reaction_pk_list = [x for x in reaction_ids if x not in reaction_2_pathways.keys]
        reaction_2_pathways = _add_links(reaction_2_pathways, REACTION_PK, PATHWAY_PK, reaction_pk_list, [NA])

        ### set everything to the request context ###

        gene_2_proteins_json = json.dumps(gene_2_proteins.mapping_list)
        protein_2_reactions_json = json.dumps(protein_2_reactions.mapping_list)
        compound_2_reactions_json = json.dumps(compound_2_reactions.mapping_list)
        reaction_2_pathways_json = json.dumps(reaction_2_pathways.mapping_list)

        rel_path = static('data/gene_names.p')
        pickled_url = self.request.build_absolute_uri(rel_path)
        metadata_map = get_gene_names(gene_ids, pickled_url)
        genes_json = _pk_to_json(GENE_PK, 'gene_id', gene_ids, metadata_map, observed_gene_df)

        # metadata_map = get_uniprot_metadata_online(uniprot_ids)
        proteins_json = _pk_to_json('protein_pk', 'protein_id', protein_ids, metadata_map, observed_protein_df)

        rel_path = static('data/compound_names.json')
        json_url = self.request.build_absolute_uri(rel_path)
        metadata_map = get_compound_metadata_from_json(compound_ids, json_url)
        compounds_json = _pk_to_json('compound_pk', 'compound_id', compound_ids, metadata_map, observed_compound_df)

        metadata_map = {}
        for name in id_to_names:
            tok = id_to_names[name]
            filtered = clean_label(tok)
            metadata_map[name] = {'display_name': filtered}

        pathway_ids = reaction_2_pathways.values
        reactions_json = _pk_to_json('reaction_pk', 'reaction_id', reaction_ids, metadata_map, None)
        pathways_json = _pk_to_json('pathway_pk', 'pathway_id', pathway_ids, metadata_map, None)

        data = {
            'genes_json': genes_json,
            'proteins_json': proteins_json,
            'compounds_json': compounds_json,
            'reactions_json': reactions_json,
            'pathways_json': pathways_json,
            'gene_proteins_json': gene_2_proteins_json,
            'protein_reactions_json': protein_2_reactions_json,
            'compound_reactions_json': compound_2_reactions_json,
            'reaction_pathways_json': reaction_2_pathways_json,
            'species': species
        }
        context = {'data': data}

        return render(self.request, self.success_url, context)


def csv_to_dataframe(csv_str):
    data = StringIO(csv_str)
    try:
        df = pd.read_csv(data)
    except pd.errors.EmptyDataError:
        df = None
    return df


def get_ids_from_dataframe(df):
    if df is None:
        return []
    else:
        return df.values[:, 0].tolist() # id is always the first column


def _pk_to_json(pk_label, display_label, data, metadata_map, observed_df):

    # turn the first column of the dataframe into index
    if observed_df is not None:
        observed_df = observed_df.set_index(observed_df.columns[0])
        observed_df = observed_df[~observed_df.index.duplicated(keep='first')] # remove row with duplicate indices

    output = []
    for item in sorted(data):

        if item == NA:
            continue # handled below after this loop

        # add primary key to row data
        row = {pk_label: item}

        # add display label to row_data
        if len(metadata_map) > 0 and item in metadata_map and metadata_map[item] is not None:
            label = metadata_map[item]['display_name']
        else:
            label = item
        row[display_label] = label

        # add the remaining data columns to row
        if observed_df is not None:
            try:
                data = observed_df.loc[item].to_dict()
            except KeyError: # missing data
                data = {}
                for col in observed_df.columns:
                    data.update({col: 0})
            row.update(data)

        output.append(row)

    # add dummy entry
    row = {pk_label: NA, display_label: NA}
    if observed_df is not None: # and the the values of the remaining columns for the dummy entry
        for col in observed_df.columns:
            row.update({col: 0})
    output.append(row)

    output_json = json.dumps(output)
    return output_json


def _make_relations(mapping, source_pk, target_pk, value_key=None):
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


def _add_dummy(relation, source_ids, target_ids, source_pk_label, target_pk_label):

    to_add = [x for x in source_ids if x not in relation.keys]
    relation = _add_links(relation, source_pk_label, target_pk_label, to_add, [NA])

    # to_add = [x for x in target_ids if x not in relation.values]
    # relation = _add_links(relation, source_pk_label, target_pk_label, [NA], to_add)

    # relation = _add_links(relation, source_pk_label, target_pk_label, [NA], [NA])
    return relation


def _add_links(relation, source_pk_label, target_pk_label, source_pk_list, target_pk_list):

    rel_mapping_list = list(relation.mapping_list)
    rel_keys = relation.keys
    rel_values = relation.values

    for s1 in source_pk_list:
        if s1 not in rel_keys: rel_keys.append(s1)
        for s2 in target_pk_list:
            rel_mapping_list.append({source_pk_label: s1, target_pk_label: s2})
            if s2 not in rel_keys: rel_values.append(s2)

    return Relation(keys=rel_keys, values=rel_values, mapping_list=rel_mapping_list)


def get_ensembl_gene_info(request):
    if request.is_ajax():
        ensembl_id = request.GET['id']
        metadata = get_single_ensembl_metadata_online(ensembl_id)

        infos = []
        selected = ['description', 'biotype', 'species']
        for key in selected:
            value = metadata[key]
            infos.append({'key': key, 'value': value})

        images = []
        links = [
            {
                'text': 'Link to Ensembl',
                'href': 'https://www.ensembl.org/id/' + ensembl_id
            }
        ]
        # for x in metadata['Transcript']:
        #     text = 'Transcript: ' + x['display_name']
        #     href = 'https://www.ensembl.org/id/' + x['id']
        #     links.append({'text': text, 'href': href})

        data = {
            'infos': infos,
            'images': images,
            'links': links
        }
        return JsonResponse(data)


def get_uniprot_protein_info(request):
    if request.is_ajax():
        uniprot_id = request.GET['id']
        metadata = get_single_uniprot_metadata_online(uniprot_id)

        infos = []
        try:
            fullname = [x.text for x in metadata.soup.select('protein > recommendedname > fullname')][0]
        except IndexError:
            fullname = uniprot_id

        shortName = None
        try:
            shortname = [x.text for x in metadata.soup.select('protein > recommendedname > shortname')][0]
        except IndexError:
            pass

        if shortName is not None:
            infos.append({'key': 'Name', 'value': "{} ({})".format(fullname, shortname) })
        else:
            infos.append({'key': 'Name', 'value': "{}".format(fullname) })

        try:
            ecnumber = [x.text for x in metadata.soup.select('protein > recommendedname > ecnumber')][0]
            infos.append({'key': 'EC Number', 'value': 'EC' + ecnumber })
        except IndexError:
            pass

        # get comments
        selected = ['function', 'catalytic activity', 'subunit']
        for child in metadata.soup.find_all('comment'):
            try:
                if child['type'] in selected:
                    infos.append({'key': child['type'], 'value': truncate(child.text)})
            except KeyError:
                continue

        # gene ontologies
        # go = []
        # for child in metadata.soup.find_all('dbreference'):
        #     try:
        #         if child['type'] == 'GO':
        #             props = child.find_all('property')
        #             for prop in props:
        #                 if prop['type'] == 'term':
        #                     go.append(prop['value'])
        #     except KeyError:
        #         continue
        # go_str = '; '.join(go)
        # go_str = truncate(go_str)
        # infos.append({'key': 'gene_ontologies', 'value': go_str})

        images = []
        # with urllib.request.urlopen('https://swissmodel.expasy.org/repository/uniprot/' + uniprot_id + '.json') as url:
        #     data = json.loads(url.read().decode())
        #     for struct in data['result']['structures']:
        #         pdb_link = struct['coordinates']
        #         images.append(pdb_link)

        links = [
            {
                'text': 'Link to UniProt',
                'href': 'http://www.uniprot.org/uniprot/' + uniprot_id
            },
            {
                'text': 'Link to SWISS-MODEL',
                'href': 'https://swissmodel.expasy.org/repository/uniprot/' + uniprot_id
            }
        ]
        data = {
            'infos': infos,
            'images': images,
            'links': links
        }
        return JsonResponse(data)


def get_swissmodel_protein_pdb(request):
    pdb_url = request.GET['pdb_url']
    with urllib.request.urlopen(pdb_url) as response:
        content = response.read()
        return HttpResponse(content, content_type="text/plain")


def get_kegg_metabolite_info(request):
    if request.is_ajax():
        kegg_id = request.GET['id']
        metadata = get_single_compound_metadata_online(kegg_id)

        infos = []
        selected = ['FORMULA']
        for key in selected:
            value = metadata[key]
            infos.append({'key': key, 'value': str(value)})

        # get pathways
        # pathway_str = '; '.join(metadata['PATHWAY'].values())
        # pathway_str = truncate(pathway_str)
        # infos.append({'key': 'KEGG PATHWAY', 'value': pathway_str})

        images = ['http://www.kegg.jp/Fig/compound/' + kegg_id + '.gif']
        links = [
            {
                'text': 'Link to KEGG compound database',
                'href': 'http://www.genome.jp/dbget-bin/www_bget?cpd:' + kegg_id
            }
        ]
        data = {
            'infos': infos,
            'images': images,
            'links': links
        }
        return JsonResponse(data)


def get_reactome_reaction_info(request):
    if request.is_ajax():
        reactome_id = request.GET['id']
        species = urllib.parse.unquote(request.GET['species'])

        infos = []
        temp = collections.defaultdict(list)
        results = get_reaction_entities([reactome_id], species)[reactome_id]
        for res in results:
            display_name = res[2]
            relationship_types = res[3]
            if len(relationship_types) == 1:  # ignore the sub-complexes
                rel = relationship_types[0]
                temp[rel].append(display_name)
        for k, v in temp.items():
            infos.append({'key': k, 'value': '; '.join(v)})

        images = [
            'https://reactome.org/ContentService/exporter/diagram/' + reactome_id + '.jpg?sel=' + reactome_id + "&quality=7"
        ]
        links = [
            {
                'text': 'Link to Reactome database',
                'href': 'https://reactome.org/content/detail/' + reactome_id
            }
        ]
        data = {
            'infos': infos,
            'images': images,
            'links': links
        }
        return JsonResponse(data)


def get_reactome_pathway_info(request):
    if request.is_ajax():
        pathway_id = request.GET['id']
        infos = []
        images = [
            'https://reactome.org/ContentService/exporter/diagram/' + pathway_id + '.jpg?sel=' + pathway_id
        ]
        links = [
            {
                'text': 'Link to Reactome database',
                'href': 'https://reactome.org/content/detail/' + pathway_id
            },
            {
                'text': 'SBML Export',
                'href': 'https://reactome.org/ContentService/exporter/sbml/' + pathway_id + '.xml'
            }
        ]
        data = {
            'infos': infos,
            'images': images,
            'links': links
        }
        return JsonResponse(data)


def truncate(my_str):
    my_str = (my_str[:TRUNCATE_LIMIT] + '...') if len(my_str) > TRUNCATE_LIMIT else my_str
    return my_str
