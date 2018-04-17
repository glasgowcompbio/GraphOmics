from django.shortcuts import render

# Create your views here.
from django.http import HttpResponse
import json
import urllib.request
import re

from django.views.generic.edit import FormView
from django.urls import reverse
from django.http import JsonResponse
from linker.forms import LinkerForm

import collections

from linker.reactome import ensembl_to_uniprot, uniprot_to_reaction
from linker.metadata import get_ensembl_metadata_online, get_uniprot_metadata_online, get_compound_metadata_online
from linker.metadata import get_single_ensembl_metadata_online, get_single_uniprot_metadata_online, get_single_compound_metadata_online
from linker.reactome import compound_to_reaction, reaction_to_metabolite_pathway, get_reaction_entities

Relation = collections.namedtuple('Relation', 'keys values mapping_list')
DUMMY_KEY = '0'  # this should be something that will appear first in the table when sorted alphabetically
DUMMY_VALUE = "---"
TRUNCATE_LIMIT = 200


class LinkerView(FormView):
    template_name = 'linker/linker.html'
    form_class = LinkerForm
    success_url = 'linker/analysis.html'

    def form_valid(self, form):
        transcripts_str = form.cleaned_data['transcripts']
        proteins_str = form.cleaned_data['proteins']
        compounds_str = form.cleaned_data['compounds']
        species = form.cleaned_data['species']

        ### maps transcript -> proteins using Reactome ###

        ensembl_ids = [x for x in iter(transcripts_str.splitlines())]
        transcript_2_proteins, transcript_2_proteins_json, id_to_names = reactome_map(species, ensembl_ids,
                                                                                      ensembl_to_uniprot,
                                                                                      'transcript_pk',
                                                                                      'protein_pk',
                                                                                      value_key=None)

        ensembl_ids = transcript_2_proteins.keys
        # metadata_map = get_ensembl_metadata(ensembl_ids)
        transcripts_json = _pk_to_json('transcript_pk', 'ensembl_id', ensembl_ids)

        ### maps proteins -> reactions using Reactome ###

        protein_ids = transcript_2_proteins.values
        protein_2_reactions, protein_2_reactions_json, id_to_names = reactome_map(species, protein_ids,
                                                                                  uniprot_to_reaction,
                                                                                  'protein_pk',
                                                                                  'reaction_pk',
                                                                                  value_key='reaction_id')

        uniprot_ids = transcript_2_proteins.values
        # metadata_map = get_uniprot_metadata_online(uniprot_ids)
        proteins_json = _pk_to_json('protein_pk', 'uniprot_id', uniprot_ids)

        ### maps compounds -> reactions using Reactome ###

        compound_ids = [x for x in iter(compounds_str.splitlines())]
        compound_2_reactions, compound_2_reactions_json, id_to_names = reactome_map(species, compound_ids,
                                                                                    compound_to_reaction,
                                                                                    'compound_pk',
                                                                                    'reaction_pk',
                                                                                    value_key='reaction_id')

        metadata_map = get_compound_metadata_online(compound_ids)
        compounds_json = _pk_to_json('compound_pk', 'kegg_id', compound_ids, metadata_map)

        ### maps reactions -> pathways using Reactome ###

        reaction_ids = protein_2_reactions.values + compound_2_reactions.values
        reaction_2_pathways, reaction_2_pathways_json, id_to_names = reactome_map(species, reaction_ids,
                                                                                  reaction_to_metabolite_pathway,
                                                                                  'reaction_pk',
                                                                                  'pathway_pk',
                                                                                  value_key='pathway_id')

        metadata_map = {}
        for name in id_to_names:
            tok = id_to_names[name]
            filtered = re.sub(r'[^\w\s]', '', tok)
            metadata_map[name] = {'display_name': filtered}

        pathway_ids = reaction_2_pathways.values
        reactions_json = _pk_to_json('reaction_pk', 'reaction_id', reaction_ids, metadata_map)
        pathways_json = _pk_to_json('pathway_pk', 'pathway_id', pathway_ids, metadata_map)

        ### set everything to the request context ###

        data = {
            'transcripts_json': transcripts_json,
            'proteins_json': proteins_json,
            'compounds_json': compounds_json,
            'reactions_json': reactions_json,
            'pathways_json': pathways_json,
            'transcript_proteins_json': transcript_2_proteins_json,
            'protein_reactions_json': protein_2_reactions_json,
            'compound_reactions_json': compound_2_reactions_json,
            'reaction_pathways_json': reaction_2_pathways_json
        }
        context = {'data': data}

        return render(self.request, self.success_url, context)


def _pk_to_json(pk_label, display_label, data, metadata_map={}):
    output = []
    for item in sorted(data):
        if len(metadata_map) > 0 and item in metadata_map and metadata_map[item] is not None:
            label = metadata_map[item]['display_name']
        else:
            label = item
        row = {pk_label: item, display_label: label}
        output.append(row)
    output.append({pk_label: DUMMY_KEY, display_label: DUMMY_VALUE})  # add dummy entry
    output_json = json.dumps(output)
    return output_json


def _make_relations(mapping_dict, all_keys, pk_label_1, pk_label_2, value_key=None):
    id_values = []
    mapping_list = []

    for key in mapping_dict:
        value_list = mapping_dict[key]

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
            row = {pk_label_1: key, pk_label_2: actual_value}
            mapping_list.append(row)

    unique_keys = set(mapping_dict.keys())
    unique_values = set(id_values)

    # insert dummy entries
    for key in all_keys:
        if key not in unique_keys:
            row = {pk_label_1: key, pk_label_2: DUMMY_KEY}
            mapping_list.append(row)
    row = {pk_label_1: DUMMY_KEY, pk_label_2: DUMMY_KEY}
    mapping_list.append(row)

    return Relation(keys=list(unique_keys), values=list(unique_values),
                    mapping_list=mapping_list)


def reactome_map(species, source_ids, mapping_func,
                 source_pk, target_pk, value_key=None):
    mapping, id_to_names = mapping_func(source_ids, species)
    relations = _make_relations(mapping, source_ids, source_pk, target_pk, value_key=value_key)
    relations_json = json.dumps(relations.mapping_list)
    return relations, relations_json, id_to_names


def clean_label(w):
    results = []
    for tok in w.split(' '):
        if 'name' not in tok.lower():
            filtered = re.sub(r'[^\w\s]', '', tok)
            results.append(filtered.strip())
    return ' '.join(results)


def get_ensembl_gene_info(request):
    if request.is_ajax():
        ensembl_id = request.GET['id']
        metadata = get_single_ensembl_metadata_online(ensembl_id)

        infos = []
        selected = ['display_name', 'description', 'biotype', 'species']
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
        selected = ['protein']
        for key in selected:
            value = metadata[key]
            infos.append({'key': key, 'value': '; '.join(map(str, value))})

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
        with urllib.request.urlopen('https://swissmodel.expasy.org/repository/uniprot/' + uniprot_id + '.json') as url:
            data = json.loads(url.read().decode())
            for struct in data['result']['structures']:
                pdb_link = struct['coordinates']
                images.append(pdb_link)

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
        pathway_str = '; '.join(metadata['PATHWAY'].values())
        pathway_str = truncate(pathway_str)
        infos.append({'key': 'KEGG PATHWAY', 'value': pathway_str})

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

        infos = []
        results = get_reaction_entities([reactome_id], 'Mus musculus')[reactome_id]
        for res in results:
            display_name = res[2]
            relationship_types = res[3]
            if len(relationship_types) == 1: # ignore the sub-complexes
                infos.append({'key': display_name, 'value': ';'.join(relationship_types)})

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
