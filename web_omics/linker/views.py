from django.shortcuts import render

# Create your views here.
from django.http import HttpResponse
import json
import re

from django.views.generic.edit import FormView
from linker.forms import LinkerForm

import collections

from linker.reactome import ensembl_to_uniprot, uniprot_to_reaction
from linker.reactome import get_ensembl_metadata, get_uniprot_metadata
from linker.reactome import compound_to_reaction, reaction_to_metabolite_pathway

Relation = collections.namedtuple('Relation', 'keys values mapping_list')
DUMMY_KEY = '0'
DUMMY_VALUE = "---"

def clean_label(w):
    results = []
    for tok in w.split(' '):
        if 'name' not in tok.lower():
            filtered = re.sub(r'[^\w\s]', '', tok)
            results.append(filtered.strip())
    return ' '.join(results)


class LinkerView(FormView):
    template_name = 'linker/linker.html'
    form_class = LinkerForm
    success_url = 'linker/analysis.html'

    def form_valid(self, form):
        # This method is called when valid form data has been POSTed.
        # It should return an HttpResponse.

        transcripts_str = form.cleaned_data['transcripts']
        proteins_str = form.cleaned_data['proteins']
        compounds_str = form.cleaned_data['compounds']
        species = form.cleaned_data['species']

        # maps transcript -> proteins using Reactome
        ensembl_ids = [x for x in iter(transcripts_str.splitlines())]
        transcript_mapping = ensembl_to_uniprot(ensembl_ids, species)
        transcript_2_proteins = _make_relations(transcript_mapping,
                                                ensembl_ids,
                                                'transcript_pk',
                                                'protein_pk')

        # maps proteins -> reactions using Reactome
        protein_ids = transcript_2_proteins.values
        protein_mapping = uniprot_to_reaction(protein_ids,
                                              species)
        protein_2_reactions = _make_relations(protein_mapping,
                                              protein_ids,
                                              'protein_pk',
                                              'reaction_pk',
                                              value_key='reaction_id')

        # maps compounds -> reactions using Reactome
        compound_ids = [x for x in iter(compounds_str.splitlines())]
        compound_mapping = compound_to_reaction(compound_ids, species)
        compound_2_reactions = _make_relations(compound_mapping,
                                               compound_ids,
                                               'compound_pk',
                                               'reaction_pk',
                                               value_key='reaction_id')

        # maps reactions -> pathways using Reactome
        # reaction_ids = protein_2_reactions.values + compound_2_reactions.values
        reaction_ids = protein_2_reactions.values
        reaction_mapping, name_lookup = reaction_to_metabolite_pathway(reaction_ids, species,
                                                                       leaf=True)
        reaction_2_pathways = _make_relations(reaction_mapping,
                                              reaction_ids,
                                              'reaction_pk',
                                              'pathway_pk',
                                              value_key='pathway_id')

        # filter relations to improve performance ?
        # print('Before %d' % len(transcript_2_proteins.mapping_list))
        # transcript_2_proteins = filter_relations_in(
        #     transcript_2_proteins,
        #     'protein_pk',
        #     set(protein_2_reactions.keys))
        # print('After %d' % len(transcript_2_proteins.mapping_list))

        # generate json dumps for the individual tables
        ensembl_ids = transcript_2_proteins.keys
        # metadata_map = get_ensembl_metadata(ensembl_ids)
        metadata_map = None

        transcripts_json = _pk_to_json('transcript_pk', 'label',
                                       ensembl_ids,
                                       metadata_map)

        uniprot_ids = transcript_2_proteins.values
        # metadata_map = get_uniprot_metadata(uniprot_ids)
        metadata_map = None

        # get from reactome -- messy!!
        # metadata_map = {}
        # for protein_id in protein_descriptions:
        #     metadata_map[protein_id] = {'display_name': protein_id}
        #     if protein_id in protein_descriptions and protein_descriptions[protein_id] is not None:
        #         desc = protein_descriptions[protein_id]
        #         tokens = desc.split(':')
        #         for i in range(len(tokens)):
        #             w = tokens[i]
        #             if w.startswith('recommendedName'):
        #                 next_w = clean_label(tokens[i+1])
        #                 metadata_map[protein_id] = {'display_name': next_w}
        #                 print(protein_id, '--', next_w)

        proteins_json = _pk_to_json('protein_pk', 'uniprot_id',
                                    uniprot_ids,
                                    metadata_map)

        compounds_json = _pk_to_json('compound_pk', 'kegg_id',
                                     compound_ids,
                                     None)

        metadata_map = {}
        for name in name_lookup:
            tok = name_lookup[name]
            filtered = re.sub(r'[^\w\s]', '', tok)
            metadata_map[name] = {'display_name': filtered}

        reactions_json = _pk_to_json('reaction_pk', 'reaction_id',
                                     reaction_ids,
                                     metadata_map)

        pathway_ids = reaction_2_pathways.values
        pathways_json = _pk_to_json('pathway_pk', 'pathway_id',
                                    pathway_ids,
                                    metadata_map)

        # dump relations to json
        transcript_2_proteins_json = json.dumps(
            transcript_2_proteins.mapping_list)

        protein_2_reactions_json = json.dumps(
            protein_2_reactions.mapping_list
        )

        compound_2_reactions_json = json.dumps(
            compound_2_reactions.mapping_list
        )

        reaction_2_pathways_json = json.dumps(
            reaction_2_pathways.mapping_list
        )

        context = {
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

        return render(self.request, self.success_url, context)


def _pk_to_json(pk_label, display_label, data, metadata_map):
    output = []
    for item in sorted(data):
        if metadata_map is not None and item in metadata_map and metadata_map[item] is not None:
            label = metadata_map[item]['display_name']
        else:
            label = item
        row = {pk_label: item, display_label: label}
        output.append(row)
    output.append({pk_label: DUMMY_KEY, display_label: DUMMY_VALUE}) # add dummy entry
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


def filter_relations_in(relation, pk_label, keep):

    filtered_list = []
    for row in relation.mapping_list:
        if row[pk_label] in keep:
            filtered_list.append(row)
    filtered_relation = Relation(
        keys=relation.keys, values=relation.values, mapping_list=filtered_list)
    return filtered_relation