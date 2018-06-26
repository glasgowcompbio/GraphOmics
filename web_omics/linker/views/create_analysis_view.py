from django.shortcuts import render, redirect
from django.views.generic.edit import FormView

from linker.forms import CreateAnalysisForm, UploadAnalysisForm
from linker.reactome import get_species_dict
from linker.views.functions import reactome_mapping, save_analysis

import pandas as pd


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

        results = reactome_mapping(self.request, genes_str, proteins_str, compounds_str, species_list)
        analysis, data = save_analysis(analysis_name, analysis_desc,
                                       genes_str, proteins_str, compounds_str,
                                       results, species_list)
        context = {
            'data': data,
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

        results = reactome_mapping(self.request, genes_str, proteins_str, compounds_str, species_list)
        analysis, data = save_analysis(analysis_name, analysis_desc,
                                       genes_str, proteins_str, compounds_str,
                                       results, species_list)
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
