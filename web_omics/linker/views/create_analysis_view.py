import pandas as pd
from django.shortcuts import render
from django.views.generic.edit import FormView

from linker.constants import DataRelationType
from linker.forms import CreateAnalysisForm, UploadAnalysisForm, AddPathwayForm, pathway_species_dict
from linker.models import AnalysisData
from linker.reactome import get_species_dict, pathway_to_reactions, reaction_to_uniprot, reaction_to_compound, \
    uniprot_to_ensembl
from linker.views.functions import reactome_mapping, save_analysis


class CreateAnalysisView(FormView):
    template_name = 'linker/create_analysis.html'
    form_class = CreateAnalysisForm
    success_url = 'linker/explore_data.html'

    def form_valid(self, form):
        analysis_name = form.cleaned_data['analysis_name']
        analysis_desc = form.cleaned_data['analysis_description']
        genes_str = form.cleaned_data['genes']
        proteins_str = form.cleaned_data['proteins']
        compounds_str = form.cleaned_data['compounds']
        species_dict = get_species_dict()
        species_list = [species_dict[x] for x in form.cleaned_data['species']]

        current_user = self.request.user
        results = reactome_mapping(self.request, genes_str, proteins_str, compounds_str, species_list)
        analysis, data = save_analysis(analysis_name, analysis_desc,
                                       genes_str, proteins_str, compounds_str,
                                       results, species_list, current_user)
        data_display_name = {}
        for k, v in DataRelationType:
            try:
                analysis_data = AnalysisData.objects.filter(analysis=analysis, data_type=k).order_by('-timestamp')[0]
                data_display_name[k] = analysis_data.display_name
            except IndexError:
                continue
            except KeyError:
                continue

        context = {
            'data': data,
            # 'data_display_name': data_display_name,
            'analysis_id': analysis.pk,
            'analysis_name': analysis.name,
            'analysis_description': analysis.description,
            'analysis_species': analysis.get_species_str()
        }
        return render(self.request, self.success_url, context)


class UploadAnalysisView(FormView):
    template_name = 'linker/upload_analysis.html'
    form_class = UploadAnalysisForm
    success_url = 'linker/explore_data.html'

    def form_valid(self, form):
        analysis_name = form.cleaned_data['analysis_name']
        analysis_desc = form.cleaned_data['analysis_description']
        genes_str = get_uploaded_data(form.cleaned_data, 'gene_data', 'gene_design')
        proteins_str = get_uploaded_data(form.cleaned_data, 'protein_data', 'protein_design')
        compounds_str = get_uploaded_data(form.cleaned_data, 'compound_data', 'compound_design')
        species_dict = get_species_dict()
        species_list = [species_dict[x] for x in form.cleaned_data['species']]
        current_user = self.request.user

        results = reactome_mapping(self.request, genes_str, proteins_str, compounds_str, species_list)
        analysis, data = save_analysis(analysis_name, analysis_desc,
                                       genes_str, proteins_str, compounds_str,
                                       results, species_list, current_user)
        context = {
            'data': data,
            'analysis_id': analysis.pk,
            'analysis_name': analysis.name,
            'analysis_description': analysis.description,
            'analysis_species': analysis.get_species_str()
        }
        return render(self.request, self.success_url, context)


class AddPathwayView(FormView):
    template_name = 'linker/add_pathway.html'
    form_class = AddPathwayForm
    success_url = 'linker/explore_data.html'

    def form_valid(self, form):
        analysis_name = form.cleaned_data['analysis_name']
        analysis_desc = form.cleaned_data['analysis_description']
        pathway_list = form.cleaned_data['pathways']
        species_list = list(set([pathway_species_dict[x] for x in pathway_list]))

        # get reactions under pathways
        pathway_2_reactions, _ = pathway_to_reactions(pathway_list)
        all_reactions = get_unique_items(pathway_2_reactions)

        # get proteins and compounds under reactions
        reaction_2_proteins, _ = reaction_to_uniprot(all_reactions, species_list)
        reaction_2_compounds, _ = reaction_to_compound(all_reactions, species_list)
        all_proteins = get_unique_items(reaction_2_proteins)
        all_compounds = get_unique_items(reaction_2_compounds)

        # get genes under proteins
        protein_2_genes, _ = uniprot_to_ensembl(all_proteins, species_list)
        all_genes = get_unique_items(protein_2_genes)

        current_user = self.request.user
        genes_str = '\n'.join(['identifier'] + all_genes)
        proteins_str = '\n'.join(['identifier'] + all_proteins)
        compounds_str = '\n'.join(['identifier'] + all_compounds)
        results = reactome_mapping(self.request, genes_str, proteins_str, compounds_str, species_list)
        analysis, data = save_analysis(analysis_name, analysis_desc,
                                       genes_str, proteins_str, compounds_str,
                                       results, species_list, current_user)
        context = {
            'data': data,
            'analysis_id': analysis.pk,
            'analysis_name': analysis.name,
            'analysis_description': analysis.description,
            'analysis_species': analysis.get_species_str()
        }
        return render(self.request, self.success_url, context)


def get_uploaded_data(form_dict, data_key, design_key):
    try:
        data = pd.read_csv(form_dict[data_key])
    except ValueError:
        data = None
    try:
        design = pd.read_csv(form_dict[design_key])
    except ValueError:
        design = None

    output_str = ''
    if data is not None and design is not None:
        output_str = get_uploaded_str(data, design)
    return output_str


def get_uploaded_str(data_df, design_df):
    data_list = data_df.to_csv(index=False).splitlines()
    sample_2_group = design_df.set_index('sample').to_dict()['group']
    first_line = data_list[0].split(',')
    second_line = ['group'] + [sample_2_group[x] for x in first_line[1:]]
    new_data_list = []
    new_data_list.append(','.join(first_line))
    new_data_list.append(','.join(second_line))
    new_data_list.extend(data_list[1:])
    data_str = '\n'.join(new_data_list)
    return data_str


def get_unique_items(mapping):
    all_items = []
    for key, values in mapping.items():
        all_items.extend(values)
    unique_items = list(set(all_items))
    return unique_items