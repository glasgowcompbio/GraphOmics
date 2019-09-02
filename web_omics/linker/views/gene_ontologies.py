import pandas as pd

from goatools.go_enrichment import GOEnrichmentStudy

from linker.views.gene_ontologies_utils import to_id, ONTOLOGIES, SPECIES_ASSOCIATIONS, GAF_NAME_TO_ID


class GOAnalysis(object):
    def __init__(self, species, namespace, background_names, significant=0.05):
        self.species = species
        self.namespace = namespace
        self.background_gene_names = background_names
        self.significant = significant

        self.ontologies = ONTOLOGIES
        self.associations = SPECIES_ASSOCIATIONS[species][namespace]
        self.names_to_id_dict = GAF_NAME_TO_ID[species]

        # convert background gene names to gene ids used in the associations
        self.background_gene_ids = to_id(self.background_gene_names, self.names_to_id_dict)

        # initialise GOEA object
        self.goea_obj = GOEnrichmentStudy(
            self.background_gene_ids,
            self.associations,
            self.ontologies,
            propagate_counts=False,
            alpha=self.significant,  # default significance cut-off
            methods=['fdr_bh'])  # defult multipletest correction method

    def goea_analysis_df(self, study_gene_names):
        goea_results_sig = self._goea_analysis(study_gene_names)
        df = self._to_dataframe(goea_results_sig)
        return df

    def _goea_analysis(self, gene_names):
        study_gene_ids = to_id(gene_names, self.names_to_id_dict)

        # 'p_' means "pvalue". 'fdr_bh' is the multipletest method we are currently using.
        goea_results_all = self.goea_obj.run_study(study_gene_ids)
        goea_results_sig = [r for r in goea_results_all if r.p_fdr_bh < self.significant]
        return goea_results_sig

    def _to_dataframe(self, goea_results_sig):
        # create a reverse dict of gene ids to names
        id_to_names = {v: k for k, v in self.names_to_id_dict.items()}
        # convert to dataframe
        data = []
        for record in goea_results_sig:
            study_ratio = record.ratio_in_study[0] / record.ratio_in_study[1]
            pop_ratio = record.ratio_in_pop[0] / record.ratio_in_pop[1]
            study_names = list(map(lambda x: id_to_names[x], record.study_items))
            row = [
                record.GO, record.name,
                study_ratio, pop_ratio,
                record.get_pvalue(), record.depth,
                record.study_count, study_names
            ]
            data.append(row)
        df = pd.DataFrame(data, columns=[
            'GO', 'name',
            'ratio_in_study', 'ratio_in_pop',
            'pvalue', 'depth',
            'study_count', 'study_items'
        ])
        df = df.set_index('GO')
        return df