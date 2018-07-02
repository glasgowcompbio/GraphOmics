from django.shortcuts import render, get_object_or_404

from linker.constants import *
from linker.models import Analysis, AnalysisData, AnalysisSample, AnalysisAnnotation

import pandas as pd
import numpy as np


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
    context = {
        'analysis_id': analysis.pk,
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
        'annotations': annotations

    }
    return render(request, 'linker/summary.html', context)


def get_counts(analysis, data_type):
    analysis_data = AnalysisData.objects.filter(analysis=analysis, data_type=data_type).first()
    json_data = analysis_data.json_data
    df = pd.DataFrame(json_data)
    cols = [c for c in df.columns if all(s not in c.lower() for s in ['pvalue', 'id', 'pk'])]
    val = df[cols].values
    s = np.sum(val, axis=1)
    total = len(s)
    observed = np.count_nonzero(s)
    inferred = total - observed - 1 # -1 to account for dummy item
    return observed, inferred, total


def get_reaction_pathway_counts(analysis):
    analysis_data = AnalysisData.objects.filter(analysis=analysis, data_type=REACTIONS).first()
    reaction_count = pd.DataFrame(analysis_data.json_data).shape[0] - 1
    analysis_data = AnalysisData.objects.filter(analysis=analysis, data_type=PATHWAYS).first()
    pathway_count = pd.DataFrame(analysis_data.json_data).shape[0] - 1
    return reaction_count, pathway_count


def get_samples(analysis, data_type):
    analysis_data = AnalysisData.objects.filter(analysis=analysis, data_type=data_type).first()
    analysis_samples = analysis_data.analysissample_set.all()
    results = [(x.sample_name, x.group_name) for x in analysis_samples]
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
