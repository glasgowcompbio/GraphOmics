from django.shortcuts import render

# Create your views here.
from django.http import HttpResponse
import json

from django.views.generic.edit import FormView
from linker.forms import LinkerForm

import collections

from linker.reactome import ensembl_to_uniprot, uniprot_to_reaction

RelationOut = collections.namedtuple('RelationOut', 'keys values json')


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
        transcript_2_proteins = _relation_to_json(transcript_mapping,
                                                  'transcript_pk',
                                                  'protein_pk')

        # maps proteins -> reactions using Reactome
        protein_mapping = uniprot_to_reaction(transcript_2_proteins.values,
                                              species)
        protein_2_reactions = _relation_to_json(protein_mapping,
                                                 'protein_pk',
                                                 'reaction_pk',
                                                 value_key='reaction_id')

        # generate json dumps for the individual tables
        transcripts_json = _pk_to_json("transcript_pk", "ensembl_id",
                                       transcript_2_proteins.keys)
        proteins_json = _pk_to_json("protein_pk", "uniprot_id",
                                    transcript_2_proteins.values)
        reactions_json = _pk_to_json("reaction_pk", "reaction_id",
                                     protein_2_reactions.values)

        context = {
            "transcripts_json": transcripts_json,
            "proteins_json": proteins_json,
            "reactions_json": reactions_json,
            "transcript_proteins_json": transcript_2_proteins.json,
            "protein_reactions_json": protein_2_reactions.json
        }

        return render(self.request, self.success_url, context)


def _pk_to_json(pk_label, display_label, data):
    output = []
    for item in data:
        row = {pk_label: item, display_label: item}
        output.append(row)
    output_json = json.dumps(output)
    return output_json


def _relation_to_json(mapping_dict, pk_label_1, pk_label_2, value_key=None):
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

    unique_keys = set(mapping_dict.keys())
    unique_values = list(set(id_values))
    mapping_json = json.dumps(mapping_list)

    return RelationOut(keys=unique_keys, values=unique_values, json=mapping_json)
