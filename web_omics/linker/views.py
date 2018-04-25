import json
import re
import urllib.request
from urllib.parse import urlparse

import collections
# Create your views here.
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
DUMMY_KEY = '0'  # this should be something that will appear first in the table when sorted alphabetically
DUMMY_VALUE = "---"
TRUNCATE_LIMIT = 200

TRANSCRIPT_PK = 'transcript_pk'
PROTEIN_PK = 'protein_pk'
COMPOUND_PK = 'compound_pk'
REACTION_PK = 'reaction_pk'
PATHWAY_PK = 'pathway_pk'


class LinkerView(FormView):
    template_name = 'linker/linker.html'
    form_class = LinkerForm
    success_url = 'linker/analysis.html'

    def form_valid(self, form):
        transcripts_str = form.cleaned_data['transcripts']
        proteins_str = form.cleaned_data['proteins']
        compounds_str = form.cleaned_data['compounds']
        species_key = int(form.cleaned_data['species'])
        species_dict = get_species_dict()
        species = species_dict[species_key]

        ### all the ids that we have from the user ###
        observed_gene_ids = [x for x in iter(transcripts_str.splitlines())]
        observed_protein_ids = [x for x in iter(proteins_str.splitlines())]
        observed_compound_ids = [x for x in iter(compounds_str.splitlines())]

        ### map genes -> proteins using Reactome ###

        gene_ids = observed_gene_ids
        mapping, id_to_names = ensembl_to_uniprot(gene_ids, species)
        transcript_2_proteins = _make_relations(mapping, TRANSCRIPT_PK, PROTEIN_PK, value_key=None)

        ### maps proteins -> reactions using Reactome ###

        inferred_protein_ids = transcript_2_proteins.values
        protein_ids = observed_protein_ids + inferred_protein_ids
        mapping, id_to_names = uniprot_to_reaction(protein_ids, species)
        protein_2_reactions = _make_relations(mapping, PROTEIN_PK, REACTION_PK, value_key='reaction_id')

        ### maps compounds -> reactions using Reactome ###

        compound_ids = observed_compound_ids
        mapping, id_to_names = compound_to_reaction(compound_ids, species)
        compound_2_reactions = _make_relations(mapping, COMPOUND_PK, REACTION_PK, value_key='reaction_id')

        ### maps reactions -> pathways using Reactome ###

        reaction_ids = list(set(protein_2_reactions.values).union(set(compound_2_reactions.values)))

        mapping, id_to_names = reaction_to_metabolite_pathway(reaction_ids, species)
        reaction_2_pathways = _make_relations(mapping, REACTION_PK, PATHWAY_PK, value_key='pathway_id')

        ### add dummy entries ###

        transcript_2_proteins = _add_dummy(transcript_2_proteins, gene_ids, protein_ids, TRANSCRIPT_PK, PROTEIN_PK)
        protein_2_reactions = _add_dummy(protein_2_reactions, protein_ids, reaction_ids, PROTEIN_PK, REACTION_PK)
        compound_2_reactions = _add_dummy(compound_2_reactions, compound_ids, reaction_ids, COMPOUND_PK, REACTION_PK)
        reaction_2_pathways = _add_dummy(reaction_2_pathways, reaction_ids, [], REACTION_PK, PATHWAY_PK)

        ### set everything to the request context ###

        transcript_2_proteins_json = json.dumps(transcript_2_proteins.mapping_list)
        protein_2_reactions_json = json.dumps(protein_2_reactions.mapping_list)
        compound_2_reactions_json = json.dumps(compound_2_reactions.mapping_list)
        reaction_2_pathways_json = json.dumps(reaction_2_pathways.mapping_list)

        rel_path = static('data/gene_names.p')
        pickled_url = self.request.build_absolute_uri(rel_path)
        metadata_map = get_gene_names(gene_ids, pickled_url)
        transcripts_json = _pk_to_json(TRANSCRIPT_PK, 'gene_id', gene_ids, metadata_map)

        # metadata_map = get_uniprot_metadata_online(uniprot_ids)
        proteins_json = _pk_to_json('protein_pk', 'protein_id', protein_ids)

        rel_path = static('data/compound_names.json')
        json_url = self.request.build_absolute_uri(rel_path)
        metadata_map = get_compound_metadata_from_json(compound_ids, json_url)
        compounds_json = _pk_to_json('compound_pk', 'compound_id', compound_ids, metadata_map)

        metadata_map = {}
        for name in id_to_names:
            tok = id_to_names[name]
            filtered = clean_label(tok)
            metadata_map[name] = {'display_name': filtered}

        pathway_ids = reaction_2_pathways.values
        reactions_json = _pk_to_json('reaction_pk', 'reaction_id', reaction_ids, metadata_map)
        pathways_json = _pk_to_json('pathway_pk', 'pathway_id', pathway_ids, metadata_map)

        data = {
            'transcripts_json': transcripts_json,
            'proteins_json': proteins_json,
            'compounds_json': compounds_json,
            'reactions_json': reactions_json,
            'pathways_json': pathways_json,
            'transcript_proteins_json': transcript_2_proteins_json,
            'protein_reactions_json': protein_2_reactions_json,
            'compound_reactions_json': compound_2_reactions_json,
            'reaction_pathways_json': reaction_2_pathways_json,
            'species': species
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


def _add_dummy(relation, source_ids, target_ids, source_pk, target_pk):
    # Create a copy as we don't want to modify the original list
    mapping_list = list(relation.mapping_list)

    # Insert dummy entries. We need to do this for the inner joins
    # across all tables to work.

    # first we add dummy entries for all the unmapped ids from the source
    for key in source_ids:
        if key not in relation.keys:
            row = {source_pk: key, target_pk: DUMMY_KEY}
            mapping_list.append(row)

    # Then we add dummy entries for all the unmapped ids from the target
    for key in target_ids:
        if key not in relation.values:
            row = {source_pk: DUMMY_KEY, target_pk: key}
            mapping_list.append(row)

    # Finally link the dummy-vs-dummy entries across
    row = {source_pk: DUMMY_KEY, target_pk: DUMMY_KEY}
    mapping_list.append(row)

    return Relation(keys=relation.keys, values=relation.values, mapping_list=mapping_list)


def reactome_map(species, source_ids, target_ids, mapping_func,
                 source_pk, target_pk, value_key=None):
    mapping, id_to_names = mapping_func(source_ids, species)
    relations = _make_relations(mapping, source_pk, target_pk,
                                value_key=value_key)
    relations = _add_dummy(relations, source_ids, target_ids,
                           source_pk, target_pk)
    relations_json = json.dumps(relations.mapping_list)
    return relations, relations_json, id_to_names


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
