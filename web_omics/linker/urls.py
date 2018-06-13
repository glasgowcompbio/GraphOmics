from django.urls import path

from . import views

urlpatterns = [

    path('create_analysis', views.CreateAnalysisView.as_view(), name='create_analysis'),
    path('explore_data/<int:analysis_id>', views.explore_data, name='explore_data'),
    path('inference/<int:analysis_id>', views.inference, name='inference'),
    path('settings/<int:analysis_id>', views.settings, name='settings'),

    path('get_ensembl_gene_info', views.get_ensembl_gene_info, name='get_ensembl_gene_info'),
    path('get_uniprot_protein_info', views.get_uniprot_protein_info, name='get_uniprot_protein_info'),
    path('get_swissmodel_protein_pdb', views.get_swissmodel_protein_pdb, name='get_swissmodel_protein_pdb'),
    path('get_kegg_metabolite_info', views.get_kegg_metabolite_info, name='get_kegg_metabolite_info'),
    path('get_reactome_reaction_info', views.get_reactome_reaction_info, name='get_reactome_reaction_info'),
    path('get_reactome_pathway_info', views.get_reactome_pathway_info, name='get_reactome_pathway_info'),

]