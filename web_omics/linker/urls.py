from django.urls import path

from . import views

urlpatterns = [
    path('', views.LinkerView.as_view(), name='linker_view'),
    path('get_ensembl_gene_info', views.get_ensembl_gene_info, name='get_ensembl_gene_info'),
    path('get_uniprot_protein_info', views.get_uniprot_protein_info, name='get_uniprot_protein_info'),
    path('get_kegg_metabolite_info', views.get_kegg_metabolite_info, name='get_kegg_metabolite_info'),
    path('get_reactome_reaction_info', views.get_reactome_reaction_info, name='get_reactome_reaction_info'),
    path('get_reactome_pathway_info', views.get_reactome_pathway_info, name='get_reactome_pathway_info'),
]