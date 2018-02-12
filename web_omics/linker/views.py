from django.shortcuts import render

# Create your views here.
from django.http import HttpResponse
import json

from django.views.generic.edit import FormView
from linker.forms import LinkerForm

from linker.reactome import ensembl_to_uniprot, uniprot_to_reaction

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

        transcripts = []
        ensembl_ids = []
        for ensembl_id in iter(transcripts_str.splitlines()):
            row = { "transcript_pk": ensembl_id, "ensembl_id": ensembl_id }
            ensembl_ids.append(ensembl_id)
            transcripts.append(row)
        transcripts_json = json.dumps(transcripts)

        print('Querying %s transcripts' % len(ensembl_ids))
        transcript_mapping = ensembl_to_uniprot(ensembl_ids, species)
        print("Results = %d" % len(transcript_mapping))

        uniprot_ids = []
        transcript_proteins = []
        for ensembl_id in transcript_mapping:
            uniprot_id = transcript_mapping[ensembl_id]
            row = {'transcript_pk': ensembl_id, "protein_pk": uniprot_id}
            transcript_proteins.append(row)
            uniprot_ids.extend(uniprot_id)
        uniprot_ids = list(set(uniprot_ids))

        proteins = []
        for uniprot_id in uniprot_ids:
            row = { "protein_pk": uniprot_id, "uniprot_id": uniprot_id }
            proteins.append(row)
        proteins_json = json.dumps(proteins)
        transcript_proteins_json = json.dumps(transcript_proteins)

        print('Querying %s proteins' % len(uniprot_ids))
        protein_mapping = uniprot_to_reaction(uniprot_ids, species)
        print("Results = %d" % len(protein_mapping))

        reaction_ids = []
        protein_reactions = []
        for uniprot_id in protein_mapping:
            reaction_id = [x['reaction_id'] for x in protein_mapping[uniprot_id]]
            row = {'protein_pk': uniprot_id, "reaction_pk": reaction_id}
            protein_reactions.append(row)
            reaction_ids.extend(reaction_id)
        reaction_ids = list(set(reaction_ids))

        reactions = []
        for reaction_id in reaction_ids:
            row = { "reaction_pk": reaction_id, "reaction_id": reaction_id }
            reactions.append(row)
        reactions_json = json.dumps(reactions)
        protein_reactions_json = json.dumps(protein_reactions)

        context = {
            "transcripts_json": transcripts_json,
            "proteins_json": proteins_json,
            "transcript_proteins_json": transcript_proteins_json,
            "reactions_json": reactions_json,
            "protein_reactions_json": protein_reactions_json
        }

        return render(self.request, self.success_url, context)