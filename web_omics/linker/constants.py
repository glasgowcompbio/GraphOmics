TRUNCATE_LIMIT = 400

NA = '-'
ALL = 'ALL'

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

T_TEST, CORRELATION, PCA, PLSDA, HIERARCHICAL, KMEANS = range(0, 6)
InferenceTypeChoices = (
    (None, NA),
    (T_TEST, 't-test'),
    # (HIERARCHICAL, 'Hierarchical Clustering'),
    # (CORRELATION, 'Correlation Analysis'),
    # (PCA, 'Principal Component Analysis'),
    # (PLSDA, 'Partial Least Square - Disciminant Analysis'),
    # (KMEANS, 'K-Means')
)

T_TEST_THRESHOLD = 0.05
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
SAMPLE_COL = 'sample'
GROUP_COL = 'group'
FACTOR_COL = 'factor'