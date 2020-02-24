import os

TRUNCATE_LIMIT = 10000

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
EXTERNAL_COMPOUND_NAMES = os.path.join(BASE_DIR, 'static', 'data', 'compound_names.p')
EXTERNAL_KEGG_TO_CHEBI = os.path.join(BASE_DIR, 'static', 'data', 'kegg_to_chebi.p')
EXTERNAL_GENE_NAMES = os.path.join(BASE_DIR, 'static', 'data', 'gene_names.p')
EXTERNAL_GO_DATA = os.path.join(BASE_DIR, 'static', 'data', 'go_data.p')

# list of default species for Add Pathways when creating new data integration analysis
# now unused since Add Pathways will be removed

ARABIDOPSIS_THALIANA = 'Arabidopsis thaliana'
BOS_TAURUS = 'Bos taurus'
CAENORHABDITIS_ELEGANS = 'Caenorhabditis elegans'
CANIS_LUPUS_FAMILIARIS = 'Canis lupus familiaris'
DANIO_RERIO = 'Danio rerio'
DICTYOSTELIUM_DISCOIDEUM = 'Dictyostelium discoideum'
DROSOPHILA_MELANOGASTER = 'Drosophila melanogaster'
GALLUS_GALLUS = 'Gallus gallus'
HOMO_SAPIENS = 'Homo sapiens'
MUS_MUSCULUS = 'Mus musculus'
ORYZA_SATIVA = 'Oryza sativa'
RATTUS_NORVEGICUS = 'Rattus norvegicus'
SACCHAROMYCES_CEREVISIAE = 'Saccharomyces cerevisiae'
SUS_SCROFA = 'Sus scrofa'

DEFAULT_SPECIES = [
    ARABIDOPSIS_THALIANA,
    BOS_TAURUS,
    CAENORHABDITIS_ELEGANS,
    CANIS_LUPUS_FAMILIARIS,
    DANIO_RERIO,
    DICTYOSTELIUM_DISCOIDEUM,
    DROSOPHILA_MELANOGASTER,
    GALLUS_GALLUS,
    HOMO_SAPIENS,
    MUS_MUSCULUS,
    ORYZA_SATIVA,
    RATTUS_NORVEGICUS,
    SACCHAROMYCES_CEREVISIAE,
    SUS_SCROFA
]

# other constants used for Firdi

NA = '-'
ALL = 'ALL'

GENE_PK = 'gene_pk'
PROTEIN_PK = 'protein_pk'
COMPOUND_PK = 'compound_pk'
REACTION_PK = 'reaction_pk'
PATHWAY_PK = 'pathway_pk'

GENOMICS, TRANSCRIPTOMICS, PROTEOMICS, METABOLOMICS, REACTIONS, PATHWAYS = range(0, 6)
AddNewDataChoices = (
    (None, NA),
    (GENOMICS, 'Gene Data'),
    (PROTEOMICS, 'Protein Data'),
    (METABOLOMICS, 'Compound Data'),
)
DataType = (
    (GENOMICS, 'Genomics'),
    (TRANSCRIPTOMICS, 'Transcriptomics'),
    (PROTEOMICS, 'Proteomics'),
    (METABOLOMICS, 'Metabolomics'),
    (REACTIONS, 'Reactions'),
    (PATHWAYS, 'Pathways')
)
TABLE_IDS = {
    GENOMICS: 'genes_table',
    PROTEOMICS: 'proteins_table',
    METABOLOMICS: 'compounds_table',
    REACTIONS: 'reactions_table',
    PATHWAYS: 'pathways_table'
}

GENES_TO_PROTEINS = 6
PROTEINS_TO_REACTIONS = 7
COMPOUNDS_TO_REACTIONS = 8
REACTIONS_TO_PATHWAYS = 9
DataRelationType = DataType + (
    (GENES_TO_PROTEINS, 'Genes to Proteins'),
    (PROTEINS_TO_REACTIONS, 'Proteins to Reactions'),
    (COMPOUNDS_TO_REACTIONS, 'Compounds to Reactions'),
    (REACTIONS_TO_PATHWAYS, 'Reaction to Pathways')
)
MAPPING = {
    GENOMICS: 'genes',
    PROTEOMICS: 'proteins',
    METABOLOMICS: 'compounds',
    REACTIONS: 'reactions',
    PATHWAYS: 'pathways',
    GENES_TO_PROTEINS: 'gene_proteins',
    PROTEINS_TO_REACTIONS: 'protein_reactions',
    COMPOUNDS_TO_REACTIONS: 'compound_reactions',
    REACTIONS_TO_PATHWAYS: 'reaction_pathways'
}

PKS = {
    GENOMICS: 'gene_pk',
    PROTEOMICS: 'protein_pk',
    METABOLOMICS: 'compound_pk'
}
IDS = {
    GENOMICS: 'gene_id',
    PROTEOMICS: 'protein_id',
    METABOLOMICS: 'compound_id'
}
IDENTIFIER_COL = 'identifier'
PADJ_COL_PREFIX = 'padj_'
FC_COL_PREFIX = 'FC_'
SAMPLE_COL = 'sample'
GROUP_COL = 'group'
FACTOR_COL = 'factor'
DEFAULT_GROUP_NAME = 'default'

COMPOUND_DATABASE_KEGG = 'KEGG'
COMPOUND_DATABASE_CHEBI = 'ChEBI'
CompoundDatabaseChoices = (
    (COMPOUND_DATABASE_KEGG, 'KEGG identifiers'),
    (COMPOUND_DATABASE_CHEBI, 'ChEBI identifiers'),
)
MetabolicPathwayOnlyChoices = (
    (True, 'Only metabolic pathways'),
    (False, 'All pathways'),
)
ShareReadOnlyChoices = (
    (True, 'Read only'),
    (False, 'Edit'),
)

# Constants used in the Inference page

INFERENCE_T_TEST = 0
INFERENCE_CORRELATION = 1
INFERENCE_PCA = 2
INFERENCE_PALS = 3
INFERENCE_ORA = 4
INFERENCE_GSEA = 5
INFERENCE_DESEQ = 6
INFERENCE_LIMMA = 7

InferenceTypeChoices = (
    (None, NA),
    (INFERENCE_T_TEST, 'Differential Expression Analysis (t-test)'),
    (INFERENCE_DESEQ, 'Differential Expression Analysis (DESeq2)'),
    (INFERENCE_LIMMA, 'Differential Expression Analysis (limma)'),
    (INFERENCE_PCA, 'Principal Component Analysis (PCA)'),
    (INFERENCE_PALS, 'Pathway Analysis (PLAGE)'),
    (INFERENCE_ORA, 'Pathway Analysis (ORA)'),
    (INFERENCE_GSEA, 'Pathway Analysis (GSEA)'),
)
SELECT_WIDGET_ATTRS = {'style': 'width: 400px'}

T_TEST_THRESHOLD = 0.05

# Pimp data import constants

PIMP_PEAK_ID_COL = 'Peak id'
PIMP_MASS_COL = 'Mass'
PIMP_RT_COl = 'RT'
PIMP_POLARITY_COL = 'Polarity'
PIMP_ANNOTATION_COL = 'PiMP Annotation'
PIMP_FRANK_ANNOTATION_COL = 'FrAnK Annotation'
PIMP_KEGG_ID_COL = 'KEGG ID'

# Gene Ontology Constants

BIOLOGICAL_PROCESS = 'BP'
CELLULAR_COMPONENT = 'CC'
MOLECULAR_FUNCTION = 'MF'
GO_NAMESPACES = [ BIOLOGICAL_PROCESS, CELLULAR_COMPONENT, MOLECULAR_FUNCTION ]

# default gene ontology files to download, see http://current.geneontology.org/products/pages/downloads.html
SPECIES_TO_GAF_PREFIX = {
    ARABIDOPSIS_THALIANA: 'tair',
    BOS_TAURUS: 'goa_cow',
    CAENORHABDITIS_ELEGANS: 'wb',
    CANIS_LUPUS_FAMILIARIS: 'goa_dog',
    DANIO_RERIO: 'zfin',
    DICTYOSTELIUM_DISCOIDEUM: 'dictybase',
    DROSOPHILA_MELANOGASTER: 'fb',
    GALLUS_GALLUS: 'goa_chicken',
    HOMO_SAPIENS: 'goa_human',
    MUS_MUSCULUS: 'mgi',
    ORYZA_SATIVA: 'gramene_oryza',
    RATTUS_NORVEGICUS: 'rgd',
    SACCHAROMYCES_CEREVISIAE: 'sgd',
    SUS_SCROFA: 'goa_pig'
}

MIN_REPLACE_GENOMICS = 10
MIN_REPLACE_PROTEOMICS_METABOLOMICS = 5000
PALS_NUM_RESAMPLES = 5000