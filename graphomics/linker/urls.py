from django.urls import path

from . import views

urlpatterns = [

    # analysis page
    path('create_analysis', views.CreateAnalysisView.as_view(), name='create_analysis'),
    path('upload_analysis', views.UploadAnalysisView.as_view(), name='upload_analysis'),
    path('delete_analysis/<int:pk>', views.DeleteAnalysisView.as_view(), name='delete_analysis'),

    # explore data views
    path('explore_data/<int:analysis_id>', views.explore_data, name='explore_data'),
    path('get_firdi_data/<int:analysis_id>', views.get_firdi_data, name='get_firdi_data'),
    path('get_heatmap_data/<int:analysis_id>', views.get_heatmap_data, name='get_heatmap_data'),
    path('explore_data/<int:analysis_id>/annotate/<int:data_type>/<str:database_id>', views.update_annotation, name='update_annotation'),

    # info panels
    path('get_ensembl_gene_info/<int:analysis_id>', views.get_ensembl_gene_info, name='get_ensembl_gene_info'),
    path('get_uniprot_protein_info/<int:analysis_id>', views.get_uniprot_protein_info, name='get_uniprot_protein_info'),
    path('get_kegg_metabolite_info/<int:analysis_id>', views.get_kegg_metabolite_info, name='get_kegg_metabolite_info'),
    path('get_reactome_reaction_info/<int:analysis_id>', views.get_reactome_reaction_info,
         name='get_reactome_reaction_info'),
    path('get_reactome_pathway_info/<int:analysis_id>', views.get_reactome_pathway_info,
         name='get_reactome_pathway_info'),
    path('get_short_info', views.get_short_info, name='get_short_info'),

    # selection group analysis
    path('save_group/<int:analysis_id>', views.save_group, name='save_group'),
    path('load_group/<int:analysis_id>', views.load_group, name='load_group'),
    path('list_groups/<int:analysis_id>', views.list_groups, name='list_groups'),
    path('get_boxplot/<int:analysis_id>', views.get_boxplot, name='get_boxplot'),
    path('get_gene_ontology/<int:analysis_id>', views.get_gene_ontology, name='get_gene_ontology'),

    # inference page
    path('inference/<int:analysis_id>', views.inference, name='inference'),
    path('inference/t_test/<int:analysis_id>', views.inference_t_test, name='inference_t_test'),
    path('inference/deseq/<int:analysis_id>', views.inference_deseq, name='inference_deseq'),
    path('inference/limma/<int:analysis_id>', views.inference_limma, name='inference_limma'),
    path('inference/pca/<int:analysis_id>', views.inference_pca, name='inference_pca'),
    path('inference/pca/results/<int:analysis_id>/<int:analysis_data_id>/<int:analysis_history_id>', views.PCAResult.as_view(), name='pca_result'),
    path('inference/pals/<int:analysis_id>', views.inference_pals, name='inference_pals'),
    path('inference/ora/<int:analysis_id>', views.inference_ora, name='inference_ora'),
    path('inference/gsea/<int:analysis_id>', views.inference_gsea, name='inference_gsea'),
    path('inference/reactome/<int:analysis_id>', views.inference_reactome, name='inference_reactome'),
    path('inference/mofa/<int:analysis_id>', views.inference_mofa, name='inference_mofa'),
    path('delete_analysis_history/<int:pk>', views.DeleteAnalysisHistoryView.as_view(), name='delete_analysis_history'),

    # mofa result page
    path('inference/mofa_result/<int:analysis_id>/<int:analysis_history_id>', views.mofa_result, name='mofa_result_page'),
    path('inference/mofa_detail_result/<int:analysis_id>/<int:analysis_history_id>', views.mofa_detail_result, name='mofa_detail_result_page'),
    path('inference/mofa_coviariance_result/<int:analysis_id>/<int:analysis_history_id>', views.mofa_coviariance_result, name='mofa_coviariance_result_page'),
    path('inference/mofa_coviariance_result_mid/<int:analysis_id>/<int:analysis_history_id>', views.mofa_coviariance_result_mid, name='mofa_coviariance_result_page_mid'),

    # summary page
    path('summary/<int:analysis_id>', views.summary, name='summary'),
    path('summary/download_list/<int:analysis_id>/<str:data_type>/<str:observed>/<str:id_or_pk>', views.download_list, name='download_list'),

    # settings page
    path('settings/<int:analysis_id>', views.settings, name='settings'),
    path('settings/add_share/<int:analysis_id>', views.add_share, name='add_share'),
    path('settings/delete_share/<int:analysis_id>/<int:share_id>', views.delete_share, name='delete_share'),
    path('settings/make_public/<int:analysis_id>', views.make_public, name='make_public'),

    # TODO: to be removed
    path('clustergrammer_demo/', views.clustergrammer_demo, name='clustergrammer_demo'),

]