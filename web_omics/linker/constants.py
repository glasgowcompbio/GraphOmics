TRUNCATE_LIMIT = 10000

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

T_TEST, CORRELATION, PCA, REACTOME = range(0, 4)
InferenceTypeChoices = (
    (None, NA),
    (T_TEST, 'DESeq2 / t-test'),
    (CORRELATION, 'Global Correlation Analysis'),
    (PCA, 'Principal Component Analysis'),
    (REACTOME, 'Reactome Analysis Service')
)
SELECT_WIDGET_ATTRS = {'style': 'width: 300px'}

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
PADJ_COL_PREFIX = 'padj_'
FC_COL_PREFIX = 'FC_'
SAMPLE_COL = 'sample'
GROUP_COL = 'group'
FACTOR_COL = 'factor'

PIMP_PEAK_ID_COL = 'Peak id'
PIMP_MASS_COL = 'Mass'
PIMP_RT_COl = 'RT'
PIMP_POLARITY_COL = 'Polarity'
PIMP_ANNOTATION_COL = 'PiMP Annotation'
PIMP_FRANK_ANNOTATION_COL = 'FrAnK Annotation'
PIMP_KEGG_ID_COL = 'KEGG ID'

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