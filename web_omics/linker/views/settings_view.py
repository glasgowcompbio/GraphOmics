import collections
import json
import pprint

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import render, get_object_or_404
from loguru import logger

from linker.constants import GENOMICS, PROTEOMICS, METABOLOMICS, DataRelationType, COMPOUND_DATABASE_KEGG
from linker.forms import AddDataForm, ShareAnalysisForm
from linker.models import Analysis, AnalysisData, Share
from linker.reactome import get_species_dict
from linker.views.functions import reactome_mapping

User = get_user_model()


def settings(request, analysis_id):
    analysis = get_object_or_404(Analysis, pk=analysis_id)
    species_dict = get_species_dict()

    # here we also set the species field to the first species of this analysis
    form_1 = AddDataForm()
    inv_map = {v: k for k, v in species_dict.items()}
    first_species = analysis.metadata['species_list'][0]
    idx = inv_map[first_species]
    form_1.fields['species'].initial = idx

    form_2 = ShareAnalysisForm()

    shares = Share.objects.filter(analysis=analysis)

    context = {
        'analysis_id': analysis.pk,
        'form_1': form_1,
        'form_2': form_2,
        'shares': shares
    }
    return render(request, 'linker/settings.html', context)


def add_share(request, analysis_id):
    if request.method == 'POST':
        analysis = get_object_or_404(Analysis, pk=analysis_id)
        form = ShareAnalysisForm(request.POST, request.FILES)
        if form.is_valid():
            username = form.cleaned_data['username']
            read_only = True if form.cleaned_data['share_type'] == 'True' else False

            # check username exists
            try:
                current_user = User.objects.get(username=username)
            except User.DoesNotExist:
                current_user = None
                messages.warning(request, 'Username %s does not exist' % username)

            if current_user is not None:
                try:
                    # try to get an existing share for this analysis under this user
                    share = Share.objects.get(analysis=analysis, user=current_user)
                    if not share.owner:
                        share.delete()  # if yes delete it, except for owner
                except Share.DoesNotExist:
                    share = None

                # now we can insert a new share
                share = Share(user=current_user, analysis=analysis, read_only=read_only, owner=False)
                share.save()

                if read_only:
                    messages.success(request, 'Analysis shared to %s in read-only mode' % current_user,
                                     extra_tags='primary')
                else:
                    messages.success(request, 'Analysis shared to %s in edit mode' % current_user,
                                     extra_tags='primary')

        else:
            messages.warning(request, 'Add share failed')

    return settings(request, analysis_id)


def delete_share(request, analysis_id, share_id):
    share = get_object_or_404(Share, pk=share_id)
    share.delete()
    messages.success(request, 'Share was successfully deleted', extra_tags='primary')
    return settings(request, analysis_id)


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

            metabolic_pathway_only = True
            results = reactome_mapping(request, genes_str, proteins_str, compounds_str, COMPOUND_DATABASE_KEGG,
                                       species_list, metabolic_pathway_only)

            # update analysis data
            counts = collections.defaultdict(int)
            for k, r in DataRelationType:
                analysis_data = AnalysisData.objects.filter(analysis=analysis, data_type=k).first()
                if analysis_data is not None:
                    new_json_data = json.loads(results[k])
                    for item in new_json_data:  # add the new data
                        if item not in analysis_data.json_data:
                            analysis_data.json_data.append(item)
                            counts[r] += 1
                    analysis_data.save()
                    logger.info('Updated analysis data %d for analysis %d' % (analysis_data.pk, analysis.pk))

            # update species in analysis metadata
            species_list = list(set(analysis.get_species_list() + species_list))
            analysis.metadata['species_list'] = species_list
            analysis.save()

            count = 1
            logger.info('Updated analysis %d (%s)' % (analysis.pk, species_list))
            messages.success(request, 'Add new data successful.', extra_tags='primary')
            s = pprint.pformat(dict(counts))
            messages.add_message(request, messages.DEBUG, 'Total records updated {0}'.format(s), extra_tags='secondary')
        else:
            messages.warning(request, 'Add new data failed.')

    return settings(request, analysis_id)


def get_formatted_data(metadata, key, database_id):
    if len(metadata[key]) == 0:  # nothing stored in the metadata
        header_line = 'identifier'
        if database_id is not None:
            new_str = header_line + '\n' + database_id
        else:
            new_str = header_line + '\n' + ''

    else:  # we found something
        header_line = metadata[key].splitlines()[0]
        toks = header_line.split(',')
        if database_id is not None:
            vals = [database_id] + [','] * (len(toks) - 1)
            assert (len(toks) == len(vals))
            new_str = header_line + '\n' + ''.join(vals)
        else:
            new_str = header_line + '\n'
    return new_str
