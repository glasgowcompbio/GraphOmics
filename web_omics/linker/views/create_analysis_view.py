import pandas as pd
import json
from django.shortcuts import render
from django.views.generic.edit import FormView

from linker.constants import DataRelationType
from linker.forms import CreateAnalysisForm, UploadAnalysisForm, AddPathwayForm, pathway_species_dict
from linker.models import AnalysisData
from linker.reactome import get_species_dict, pathway_to_reactions, reaction_to_uniprot, reaction_to_compound, \
    uniprot_to_ensembl
from linker.views.functions import reactome_mapping, save_analysis
from linker.constants import *


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

        analysis, data, data_fields = get_data(self.request, analysis_desc, analysis_name, compounds_str, current_user,
                                               genes_str, proteins_str, species_list)
        context = get_context(analysis, data, data_fields)
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

        analysis, data, data_fields = get_data(self.request, analysis_desc, analysis_name, compounds_str, current_user,
                                               genes_str, proteins_str, species_list)
        context = get_context(analysis, data, data_fields)
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

        analysis, data, data_fields = get_data(self.request, analysis_desc, analysis_name, compounds_str, current_user,
                                               genes_str, proteins_str, species_list)
        context = get_context(analysis, data, data_fields)
        return render(self.request, self.success_url, context)


def get_data(request, analysis_desc, analysis_name, compounds_str, current_user, genes_str, proteins_str,
             species_list):
    results = reactome_mapping(request, genes_str, proteins_str, compounds_str, species_list)
    analysis, data = save_analysis(analysis_name, analysis_desc,
                                   genes_str, proteins_str, compounds_str,
                                   results, species_list, current_user)
    table_names = {
        GENOMICS: 'genes_table',
        PROTEOMICS: 'proteins_table',
        METABOLOMICS: 'compounds_table'
    }
    data_fields = {}
    for k, v in DataRelationType:
        try:
            analysis_data = AnalysisData.objects.filter(analysis=analysis, data_type=k).order_by('-timestamp')[0]
            if analysis_data.json_design:
                data_fields[table_names[k]] = list(
                    set(pd.DataFrame(json.loads(analysis_data.json_design))[SAMPLE_COL]))
        except IndexError:
            continue
        except KeyError:
            continue
    return analysis, data, data_fields


def get_context(analysis, data, data_fields):
    context = {
        'data': data,
        'data_fields': json.dumps(data_fields),
        'analysis_id': analysis.pk,
        'analysis_name': analysis.name,
        'analysis_description': analysis.description,
        'analysis_species': analysis.get_species_str()
    }
    return context


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
    if data is not None:
        output_str = get_uploaded_str(data, design)
    return output_str


def get_uploaded_str(data_df, design_df):
    # check if it's a PiMP peak-table export format
    if 'Peak id' in data_df.columns:
        # remove unwanted columns
        to_drop = ['Peak id', 'Mass', 'RT', 'Polarity']
        if 'FrAnK Annotation' in data_df.columns:
            to_drop.append('FrAnK Annotation')
        if 'PiMP Annotation' in data_df.columns:
            to_drop.append('PiMP Annotation')
        data_df = data_df.drop(to_drop, axis=1)
        # format dataframe: each kegg compound is a row by itself
        data_list = []
        for i, row in data_df.iterrows():
            compound_ids = row['KEGG ID']
            try:
                for compound_id in compound_ids.split(','):
                    if compound_id.strip().startswith('C'):
                        row_dict = row.drop('KEGG ID').to_dict()
                        row_dict[IDENTIFIER_COL] = compound_id
                        data_list.append(row_dict)
            except TypeError:
                continue
            except AttributeError:
                continue
        data_df = pd.DataFrame(data_list)
        data_df = change_column_order(data_df, IDENTIFIER_COL, 0) # assume it's the first column always

    # convert to csv since that's what subsequent methods want, adding the second grouping line if necessary
    data_list = data_df.to_csv(index=False).splitlines()
    first_line = data_list[0].split(',')

    if design_df is not None:
        design_df.columns = design_df.columns.str.lower()
        sample_2_group = design_df.set_index(SAMPLE_COL).to_dict()[GROUP_COL]
        second_line = [GROUP_COL] + [sample_2_group[x] for x in first_line[1:]]
    else: # assigns a default group if the design matrix is not provided
        second_line = [GROUP_COL] + ['default' for x in first_line[1:]]

    # remove period from sample name since this can break alasql
    first_line = [w.replace('.', '_') for w in first_line]
    new_data_list = []
    new_data_list.append(','.join(first_line))
    new_data_list.append(','.join(second_line))
    new_data_list.extend(data_list[1:])
    data_str = '\n'.join(new_data_list)
    return data_str


def change_column_order(df, col_name, index):
    cols = df.columns.tolist()
    cols.remove(col_name)
    cols.insert(index, col_name)
    return df[cols]


def get_unique_items(mapping):
    all_items = []
    for key, values in mapping.items():
        all_items.extend(values)
    unique_items = list(set(all_items))
    return unique_items
