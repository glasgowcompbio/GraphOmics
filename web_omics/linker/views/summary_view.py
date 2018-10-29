from django.shortcuts import render, get_object_or_404

from linker.constants import *
from linker.models import Analysis, AnalysisData, AnalysisAnnotation

import json
import pandas as pd
import numpy as np
from clustergrammer import Network

from linker.views import get_last_analysis_data
from linker.views.functions import get_last_analysis_data, get_groups, get_dataframes, filter_data
from linker.constants import *


def summary(request, analysis_id):
    analysis = get_object_or_404(Analysis, pk=analysis_id)
    observed_genes, inferred_genes, total_genes = get_counts(analysis, GENOMICS)
    observed_proteins, inferred_proteins, total_proteins = get_counts(analysis, PROTEOMICS)
    observed_compounds, inferred_compounds, total_compounds = get_counts(analysis, METABOLOMICS)
    reaction_count, pathway_count = get_reaction_pathway_counts(analysis)
    gene_samples = get_samples(analysis, GENOMICS)
    protein_samples = get_samples(analysis, PROTEOMICS)
    compound_samples = get_samples(analysis, METABOLOMICS)
    annotations = get_annotations(analysis)
    compound_database = analysis.metadata['compound_database_str']
    cluster_json = get_clusters(analysis, [GENOMICS, PROTEOMICS, METABOLOMICS])
    data = {
        'observed_genes': observed_genes,
        'observed_proteins': observed_proteins,
        'observed_compounds': observed_compounds,
        'inferred_genes': inferred_genes,
        'inferred_proteins': inferred_proteins,
        'inferred_compounds': inferred_compounds,
        'total_genes': total_genes,
        'total_proteins': total_proteins,
        'total_compounds': total_compounds,
        'num_reactions': reaction_count,
        'num_pathways': pathway_count,
        'gene_samples': gene_samples,
        'protein_samples': protein_samples,
        'compound_samples': compound_samples,
        'annotations': annotations,
        'compound_database': compound_database,
    }
    react_props = {
        'cluster_json': cluster_json
    }
    context = {
        'analysis_id': analysis.pk,
        'data': data,
        'react_props': json.dumps(react_props)
    }
    return render(request, 'linker/summary.html', context)


def get_counts(analysis, data_type):
    analysis_data = get_last_analysis_data(analysis, data_type)
    json_data = analysis_data.json_data
    df = pd.DataFrame(json_data)
    observed = df[df['obs'] == True].shape[0]
    inferred = df[df['obs'] == False].shape[0] - 1 # -1 to account for dummy item
    total = observed + inferred
    return observed, inferred, total


def get_reaction_pathway_counts(analysis):
    analysis_data = AnalysisData.objects.filter(analysis=analysis, data_type=REACTIONS).first()
    reaction_count = pd.DataFrame(analysis_data.json_data).shape[0] - 1
    analysis_data = AnalysisData.objects.filter(analysis=analysis, data_type=PATHWAYS).first()
    pathway_count = pd.DataFrame(analysis_data.json_data).shape[0] - 1
    return reaction_count, pathway_count


def get_samples(analysis, data_type):
    analysis_data = AnalysisData.objects.filter(analysis=analysis, data_type=data_type).first()
    if analysis_data.json_design is not None:
        df = pd.DataFrame(json.loads(analysis_data.json_design))
        df.insert(1, FACTOR_COL, GROUP_COL)
        df.sort_values(by=SAMPLE_COL, inplace=True)
        results = df.values
    else:
        results = []
    return results


def get_annotations(analysis):
    annotations = AnalysisAnnotation.objects.filter(analysis=analysis).order_by('data_type', 'database_id')
    results = []
    for annot in annotations:
        url = get_url(annot.data_type, annot.database_id)
        results.append((to_label(annot.data_type), annot.database_id, annot.annotation, url, annot.display_name))
    return results


def to_label(data_type):
    keys = [GENOMICS, PROTEOMICS, METABOLOMICS, REACTIONS, PATHWAYS]
    values = ['Gene Data', 'Protein Data', 'Compound Data', 'Reaction Data', 'Pathway Data']
    mapping = dict(zip(keys, values))
    return mapping[data_type]


def get_url(data_type, database_id):
    if data_type == GENOMICS:
        return 'https://www.ensembl.org/id/' + database_id
    elif data_type == PROTEOMICS:
        return 'http://www.uniprot.org/uniprot/' + database_id
    elif data_type == METABOLOMICS:
        return 'https://www.ebi.ac.uk/chebi/searchId.do?chebiId=CHEBI:' + database_id
    elif data_type == REACTIONS or data_type == PATHWAYS:
        return 'https://reactome.org/content/detail/' + database_id


def get_clusters(analysis, data_types):
    cluster_json = {}
    for data_type in data_types:
        analysis_data = get_last_analysis_data(analysis, data_type)
        data_df, design_df = get_dataframes(analysis_data, PKS[data_type], SAMPLE_COL)
        data_df = filter_data(data_df, data_type)
        if not data_df.empty:
            # df = np.log2(data_df.replace(0, 1))
            df = data_df
            net = Network()
            net.load_df(df)
            # net.filter_sum('row', threshold=20)
            net.normalize(axis='col', norm_type='zscore')
            net.filter_N_top('row', 1000, rank_type='var')
            # net.filter_threshold('row', threshold=3.0, num_occur=4)
            # net.swap_nan_for_zero()
            # net.downsample(ds_type='kmeans', axis='col', num_samples=10)
            # net.random_sample(random_state=100, num_samples=10, axis='col')
            net.cluster()
            json_data = net.export_net_json()
            if data_type == GENOMICS:
                label = 'gene'
            elif data_type == PROTEOMICS:
                label = 'protein'
            elif data_type == METABOLOMICS:
                label = 'compound'
            cluster_json[label] = json_data
    return cluster_json
