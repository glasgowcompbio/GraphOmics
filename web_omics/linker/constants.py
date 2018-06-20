TRUNCATE_LIMIT = 400

GENOMICS, TRANSCRIPTOMICS, PROTEOMICS, METABOLOMICS, REACTIONS, PATHWAYS = range(0, 6)
AddNewDataChoices = (
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

FOLD_CHANGE, T_TEST, CORRELATION, PCA, PLSDA, HIERARCHICAL, KMEANS = range(0, 7)
InferenceType = (
    (FOLD_CHANGE, 'Fold Change'),
    (T_TEST, 'Transcriptomics'),
    (CORRELATION, 'Proteomics'),
    (PCA, 'Principal Component Analysis'),
    (PLSDA, 'Partial Least Square - Disciminant Analysis'),
    (HIERARCHICAL, 'Hierarchical Clustering'),
    (KMEANS, 'K-Means')
)