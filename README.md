# Welcome!

![Logo](graphomics/images/transparent_banner.png?raw=true "Logo")

GraphOmics is a dashboard to integrate and explore different types of biological -omics data. 
Using this tool, you can map transcriptomics, proteomics and metabolomics data onto metabolic pathways. 
GraphOmics uses [Reactome](https://reactome.org/) as the knowledge base to map entities across different omics.
Methods to rank pathway and highlight interesting connection are also included.

Features include:
- A **Data Browser** which shows all the interconnected transcripts, proteins, metabolites, reactions and pathways in your data, alongside their fold-change measurements colour-coded by their p-value significance. Entities can be filtered, sorted and searched in the Data Browser.
- For **interactive heatmap visualisation**, GraphOmics uses [Clustergrammer](https://amp.pharm.mssm.edu/clustergrammer/), a web-based tool for visualizing and analyzing high-dimensional data as interactive clustered heatmaps.
The heatmap is linked to the Data Browser such that anything that is clicked on one will also be selected on the other.
A cluster can also be selected from the heatmap in Clustergrammer and be used to create selection group for further analysis in GraphOmics.
- A **selection group** can be created from the Data Browser or the Clustergrammer heatmap for further analysis. At the moment, users can create a boxplot or perform gene ontology analysis on a group.
- The **pathway analysis** functionalities used in GraphOmics have been separated into a stand-alone Python library **PALS** that can be used outside this project. This includes pathway analysis using ORA, GSEA and PLAGE on transcripts (Ensembl ID), proteins (UniProt ID)
and compound (KEGG or ChEBI IDs) from the Reactome or KEGG database. For more details, please refer to [PALS](http://pals.glasgowcompbio.org).
Integrated analysis spanning multiple omics data is also possible through [Reactome Analysis Service](https://reactome.org/dev/analysis).
- Gene Ontology Analysis, PCA, heatmaps and various other plots can also be generated from GraphOmics.

## Running GraphOmics

An instance of GraphOmics is hosted at Glasgow Polyomics and can be accessed from [https://graphomics.glasgowcompbio.org/app/](https://graphomics.glasgowcompbio.org/app/). Alternatively you could also run your own instance by following the [setup guide](setup_guide.md).

**Requirement**:
- Django 3.0, with Python and rpy for backend.
- A local Reactome installation.
- The usual scientific python stack (Numpy/Scipy/Pandas) for analysis and running the notebooks (optional).

## Using GraphOmics

[User guide](user_guide.md) to complete an integrated omics analysis using GraphOmics can be found here.

GraphOmics has also been published in **[BMC Bioinformatics](https://bmcbioinformatics.biomedcentral.com/articles/10.1186/s12859-021-04500-1).**

Finally a Python package to perform multi-omics data linking and analysis is available at [https://github.com/glasgowcompbio/pyMultiOmics](https://github.com/glasgowcompbio/pyMultiOmics). This is the same code used in this Web application but available for stand-alone use in your own application.

If you have any feedback, bug reports or would like to contribute to the development of GraphOmics, please raise an issue on this Github.
