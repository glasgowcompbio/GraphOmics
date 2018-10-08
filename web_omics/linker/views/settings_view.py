import json
import collections
import pprint

from django.shortcuts import render, get_object_or_404
from django.contrib import messages

from linker.forms import AddDataForm, AddPathwayForm
from linker.models import Analysis, AnalysisData
from linker.reactome import get_species_dict
from linker.views.functions import reactome_mapping, save_analysis
from linker.constants import GENOMICS, PROTEOMICS, METABOLOMICS, REACTIONS, PATHWAYS, DataRelationType


def settings(request, analysis_id):
    analysis = get_object_or_404(Analysis, pk=analysis_id)
    species_dict = get_species_dict()

    # here we also set the species field to the first species of this analysis
    form = AddDataForm()
    inv_map = {v: k for k, v in species_dict.items()}
    first_species = analysis.metadata['species_list'][0]
    idx = inv_map[first_species]
    form.fields['species'].initial = idx

    context = {
        'analysis_id': analysis.pk,
        'form': form,
    }
    return render(request, 'linker/settings.html', context)


def add_data(request, analysis_id):
    if request.method == 'POST':
        analysis = get_object_or_404(Analysis, pk=analysis_id)
        species_dict = get_species_dict()
        form = AddDataForm(request.POST, request.FILES)
        if form.is_valid():
            database_id = form.cleaned_data['database_id']
            species = form.cleaned_data['species']
            species_list = [species_dict[species]]
            data_type = int(form.cleaned_data['data_type'])

            if data_type == GENOMICS:
                genes_str = get_formatted_data(analysis.metadata, 'genes_str', database_id)
                proteins_str = get_formatted_data(analysis.metadata, 'proteins_str', None)
                compounds_str = get_formatted_data(analysis.metadata, 'compounds_str', None)
            elif data_type == PROTEOMICS:
                genes_str = get_formatted_data(analysis.metadata, 'genes_str', None)
                proteins_str = get_formatted_data(analysis.metadata, 'proteins_str', database_id)
                compounds_str = get_formatted_data(analysis.metadata, 'compounds_str', None)
            elif data_type == METABOLOMICS:
                genes_str = get_formatted_data(analysis.metadata, 'genes_str', None)
                proteins_str = get_formatted_data(analysis.metadata, 'proteins_str', None)
                compounds_str = get_formatted_data(analysis.metadata, 'compounds_str', database_id)

            results = reactome_mapping(request, genes_str, proteins_str, compounds_str,
                                       species_list, metabolic_pathway_only)

            # update analysis data
            counts = collections.defaultdict(int)
            for k, r in DataRelationType:
                analysis_data = AnalysisData.objects.filter(analysis=analysis, data_type=k).first()
                if analysis_data is not None:
                    new_json_data = json.loads(results[k])
                    for item in new_json_data: # add the new data
                        if item not in analysis_data.json_data:
                            analysis_data.json_data.append(item)
                            counts[r] += 1
                    analysis_data.save()
                    print('Updated analysis data', analysis_data.pk, 'for analysis', analysis.pk)

            # update species in analysis metadata
            species_list = list(set(analysis.get_species_list() + species_list))
            analysis.metadata['species_list'] = species_list
            analysis.save()

            count = 1
            print('Updated analysis', analysis.pk, '(', species_list, ')')
            messages.success(request, 'Add new data successful.', extra_tags='primary')
            s = pprint.pformat(dict(counts))
            messages.add_message(request, messages.DEBUG, 'Total records updated {0}'.format(s), extra_tags='secondary')
        else:
            messages.warning(request, 'Add new data failed.')

    return settings(request, analysis_id)


def get_formatted_data(metadata, key, database_id):
    if len(metadata[key]) == 0: # nothing stored in the metadata
        header_line = 'identifier'
        if database_id is not None:
            new_str = header_line + '\n' + database_id
        else:
            new_str = header_line + '\n' + ''

    else: # we found something
        header_line = metadata[key].splitlines()[0]
        toks = header_line.split(',')
        if database_id is not None:
            vals = [database_id] + [','] * (len(toks)-1)
            assert(len(toks) == len(vals))
            new_str = header_line + '\n' + ''.join(vals)
        else:
            new_str = header_line + '\n'
    return new_str