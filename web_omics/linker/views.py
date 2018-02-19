from django.shortcuts import render

# Create your views here.
from django.http import HttpResponse
import json

from django.views.generic.edit import FormView
from linker.forms import LinkerForm

import collections

from linker.reactome import ensembl_to_uniprot, uniprot_to_reaction

Relation = collections.namedtuple('Relation', 'keys values mapping_list')


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
                                                'transcript_pk',
                                                'protein_pk')

        # maps proteins -> reactions using Reactome
        protein_mapping = uniprot_to_reaction(transcript_2_proteins.values,
                                              species)
        protein_2_reactions = _make_relations(protein_mapping,
                                              'protein_pk',
                                              'reaction_pk',
                                              value_key='reaction_id')

        # filter relations to improve performance ?
        print("Before %d" % len(transcript_2_proteins.mapping_list))
        transcript_2_proteins = filter_relations_in(
            transcript_2_proteins,
            'protein_pk',
            set(protein_2_reactions.keys))
        print("After %d" % len(transcript_2_proteins.mapping_list))


        # generate json dumps for the individual tables
        transcripts_json = _pk_to_json("transcript_pk", "ensembl_id",
                                       transcript_2_proteins.keys)
        proteins_json = _pk_to_json("protein_pk", "uniprot_id",
                                    transcript_2_proteins.values)
        reactions_json = _pk_to_json("reaction_pk", "reaction_id",
                                     protein_2_reactions.values)

        # dump relations to json
        transcript_2_proteins_json = json.dumps(
            transcript_2_proteins.mapping_list)
        protein_2_reactions_json = json.dumps(
            protein_2_reactions.mapping_list
        )

        context = {
            "transcripts_json": transcripts_json,
            "proteins_json": proteins_json,
            "reactions_json": reactions_json,
            "transcript_proteins_json": transcript_2_proteins_json,
            "protein_reactions_json": protein_2_reactions_json
        }

        return render(self.request, self.success_url, context)


def _pk_to_json(pk_label, display_label, data):
    output = []
    for item in sorted(data):
        row = {pk_label: item, display_label: item}
        output.append(row)
    output_json = json.dumps(output)
    return output_json


def _make_relations(mapping_dict, pk_label_1, pk_label_2, value_key=None):
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
                assert value_key is not None, "value_key is missing"
                actual_value = value[value_key]
            id_values.append(actual_value)
            row = {pk_label_1: key, pk_label_2: actual_value}
            mapping_list.append(row)

    unique_keys = list(set(mapping_dict.keys()))
    unique_values = list(set(id_values))

    return Relation(keys=unique_keys, values=unique_values,
                    mapping_list=mapping_list)


def filter_relations_in(relation, pk_label, keep):

    filtered_list = []
    for row in relation.mapping_list:
        if row[pk_label] in keep:
            filtered_list.append(row)
    filtered_relation = Relation(
        keys=relation.keys, values=relation.values, mapping_list=filtered_list)
    return filtered_relation
