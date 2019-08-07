from django.urls import path

from . import views

urlpatterns = [

    path('create_analysis', views.CreateAnalysisView.as_view(), name='create_analysis'),
    path('upload_analysis', views.UploadAnalysisView.as_view(), name='upload_analysis'),
    path('delete_analysis/<int:pk>', views.DeleteAnalysisView.as_view(), name='delete_analysis'),
    path('add_pathway', views.AddPathwayView.as_view(), name='add_pathway'),

    path('explore_data/<int:analysis_id>', views.explore_data, name='explore_data'),
    path('get_firdi_data/<int:analysis_id>', views.get_firdi_data, name='get_firdi_data'),
    path('get_heatmap_data/<int:analysis_id>', views.get_heatmap_data, name='get_heatmap_data'),

    path('explore_data/<int:analysis_id>/annotate/<int:data_type>/<str:database_id>', views.update_annotation, name='update_annotation'),
    path('save_group/<int:analysis_id>', views.save_group, name='save_group'),
    path('load_group/<int:analysis_id>', views.load_group, name='load_group'),
    path('list_groups/<int:analysis_id>', views.list_groups, name='list_groups'),
    path('get_ensembl_gene_info/<int:analysis_id>', views.get_ensembl_gene_info, name='get_ensembl_gene_info'),
    path('get_uniprot_protein_info/<int:analysis_id>', views.get_uniprot_protein_info, name='get_uniprot_protein_info'),
    path('get_kegg_metabolite_info/<int:analysis_id>', views.get_kegg_metabolite_info, name='get_kegg_metabolite_info'),
    path('get_reactome_reaction_info/<int:analysis_id>', views.get_reactome_reaction_info,
         name='get_reactome_reaction_info'),
    path('get_reactome_pathway_info/<int:analysis_id>', views.get_reactome_pathway_info,
         name='get_reactome_pathway_info'),
    path('get_short_info', views.get_short_info, name='get_short_info'),

    path('inference/<int:analysis_id>', views.inference, name='inference'),
    path('inference/t_test/<int:analysis_id>', views.inference_deseq_t_test, name='inference_deseq_t_test'),
    path('inference/pca/<int:analysis_id>', views.inference_pca, name='inference_pca'),
    path('inference/pca/results/<int:analysis_id>/<int:analysis_data_id>/', views.PCAResult.as_view(), name='pca_result'),

    path('summary/<int:analysis_id>', views.summary, name='summary'),
    path('summary/download_list/<int:analysis_id>/<str:data_type>/<str:observed>/<str:id_or_pk>', views.download_list, name='download_list'),

    path('settings/<int:analysis_id>', views.settings, name='settings'),
    path('settings/add_data/<int:analysis_id>', views.add_data, name='add_data'),

    path('clustergrammer_demo/', views.clustergrammer_demo, name='clustergrammer_demo'),

]