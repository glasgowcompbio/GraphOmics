# GraphOmics User Guide

The following user guide describes a typical workflow of a GraphOmics analysis starting from data uploading, interactive
data exploration and potential hypothesis discovery through multi-omics data integration and analysis on the GraphOmics
platform.

Throughout this user guide, we will use as an example the Covid-19 dataset
from [Proteomic and Metabolomic Characterization of COVID-19 Patient Sera](https://www.sciencedirect.com/science/article/pii/S0092867420306279)
. The dataset comprise of a dual-omics (proteomics and metabolomics) study on the sera of a cohort of 28 severe Covid-19
patients in comparison to a cohort of 28 healthy patients. Analysis of this data is also performed in the GraphOmics
paper under the **'Covid-19 Case Study'** section.

## 1. Data Uploading

The first step to performing analysis on GraphOmics is to upload your data to the platform. To do this, head to
the [main page of GraphOmics](https://graphomics.glasgowcompbio.org/app/). You will list the list of analysis currently
owned or shared with you. At the bottom of the screen, click the **[Create a New Data Integration Analysis]** button.
You will see a screen that lets you enter or upload your data.

![Data Explorer](graphomics/images/userguide01.PNG?raw=true "Data Explorer")

### a. Enter Data

From the Enter Data page that shows, you can upload your data in CSV format. The format is documented on the page
itself (click the **[Data Format]** button), and is also reproduced here:

> Create a new data integration analysis by entering its data below in comma-separated values format.
>
> Analysis description is optional and can be left blank.
>
> Other fields for the data should be provided in a comma-separated format.
>
> For each -omics data:
> - The first row is the header, and the first column is always used as the identifier column.
> - Other columns are taken as the sample measurements.
> - If present, a second row that begins with group can also be provided to specify the grouping information.

To load example Covid-19 data that we will use throughout this user guide, click the **[Example Data]** button.

![Enter Data](graphomics/images/userguide02.PNG?raw=true "Enter Data")
Once you've entered all the data, click the **[Submit Your Analysis]** button. The analysis will upload. It might take a
while until it is completed, so please be patient.

### b. Upload Data

Alternatively you can also upload data that is already available in CSV format into the system. The format used is
similar to the above, but here you can also upload additional CSV files that specify the design matrix, including group
assignments and other factors that are relevant to particular samples.

![Upload Data](graphomics/images/userguide03.PNG?raw=true "Upload Data")
To view description of the data format, click the **[Data Format]** button. The same description can also be found
below. 

> Create a new data integration analysis by uploading data following the example format below.
> - Analysis description is optional and can be left blank.
> - Other fields for the data should be provided in a comma-separated format.
> - For each omics data available, the following two files should be provided, otherwise they can be left blank.
>  1. [Measurements in CSV format](https://graphomics.glasgowcompbio.org/static/data/uploads/compound_data.4aaef9af536e.csv)
>  2. [Design matrix in CSV format](https://graphomics.glasgowcompbio.org/static/data/uploads/compound_design.1c2b296d8756.csv)

To view example data, click the **[Example Data]** button. Two example data are provided:
1. Example [Zebrafish dataset](https://graphomics.glasgowcompbio.org/static/data/uploads/zebrafish_data.04658da363c9.zip) [[1]](https://www.pnas.org/content/114/5/E717)
2. Example [Covid19 dataset](https://graphomics.glasgowcompbio.org/static/data/uploads/covid19_data.b4df58372dba.zip) [[2]](https://www.cell.com/cell/fulltext/S0092-8674(20)30627-9)

The **Limit to** options restricts whether to map entities to all pathways found in Reactome, or metabolic pathways only.

The **Query compounds by** options determines whether to map metabolite entities based on their KEGG or ChEBI IDs. You might get different results
depending on which identifier is used depending on Reactome coverage of those compounds.

Once you've entered all the data, click the **[Submit Your Analysis]** button. The analysis will upload. It might take a
while until it is completed, so please be patient.

## 2. Interactive Omics Data Exploration

Uploaded data containing transcripts, proteins and metabolite entities are mapped to Reactome's reactions and pathways during horizontal omics integration.
**Note that any entities that can't be mapped, where no information is available on that entity in Reactome, will be dropped**.
The integrated omics data can now be browsed through various views in GraphOmics. Significantly changing entities can be examined can be examined in relation to other connected
entities and to reactions and pathways, and to clustering information. Pathways could also be ranked by their activity levels. The following
sections explain how interactive data exploration could be done in GraphOmics.

### a. Data Browser

The Data Browser is the primary interface in GraphOmics that facilitate linked explorations of multi-modals transcripts, proteins and metabolite data.
From the Data Browser, users could click an entity, e.g. a protein, and the relationships of that protein to other entities (transcripts, metabolites, reactions and pathways) will be revealed.
This makes it easy for users to examine the context in which a significantly changing entity is found.

![Data Browser](graphomics/images/userguide04.PNG?raw=true "Data Browser")
In the example below, we select a particular protein of interest [P02776](https://www.uniprot.org/uniprot/P02776) (for gene Platelet Factor 4, or PF4) from the Data Browser.
PF4 is released during platelet aggregation, and [existing literature](https://analyticalsciencejournals.onlinelibrary.wiley.com/doi/full/10.1002/elps.201200002) found that changes to PF4 is a prognosis marker in severe acute respiratory syndrome.

![Selecting a protein](graphomics/images/userguide05.PNG?raw=true "Data Browser")
From the Data Browser screen above, we can easily read off the following information:
- Protein P02776 has a log2-fold change of 0.35 from the case (severe Covid-19) to the control (healthy) case. 
- Hovering the mouse over displays the adjusted p-value of 9.0106e-3 from limma analysis of the differential expression of that protein between the two groups.
- The connection between protein P02776 to other entities, such as compounds and pathways are shown. We can immediately see ...
