import pandas as pd
from goatools.associations import read_gaf
from goatools.base import dnld_gaf
from goatools.base import download_go_basic_obo
from goatools.obo_parser import GODag

from linker.common import load_obj, save_obj
from linker.constants import *


def download_ontologies():
    """
    Download ontologies, a dictionary that maps GO IDs to GO terms. In most cases, we should use the basic OBO file.
    :return: a dictionary where key is the gene ontology id ('GO:0000001') and value is the GOTerm class
    """
    obo_fname = download_go_basic_obo(prt=None, loading_bar=False)
    ontologies = GODag(obo_fname)
    return ontologies


def gaf_names_to_id(gaf_filename):
    df = pd.read_csv(gaf_filename, comment='!', sep='\t', header=None, dtype=str)

    # temp has 2 columns. First is the gene id, next is the gene symbol
    # example:
    # 'ZDB-MIRNAG-081210-6', 'mir26b'
    temp = df.iloc[:, 1:3].values
    names_to_id = {symbol: my_id for my_id, symbol in temp}
    return names_to_id


def to_id(names, names_to_id_dict):
    ids = []
    for x in names:
        try:
            my_id = names_to_id_dict[x.lower()]
            ids.append(my_id)
        except KeyError as e:
            # print(e)
            pass
    return ids


def download_associations():
    SPECIES_ASSOCIATIONS = {}
    GAF_NAME_TO_ID = {}
    i = 0
    for species, gaf_prefix in SPECIES_TO_GAF_PREFIX.items():
        i += 1
        print('%d/%d Loading associations for %s (%s.gaf)' % (i, len(SPECIES_TO_GAF_PREFIX), species, gaf_prefix))

        gaf_filename = dnld_gaf(gaf_prefix, prt=None, loading_bar=False)
        GAF_NAME_TO_ID[species] = gaf_names_to_id(gaf_filename)

        assocs = {}
        for namespace in GO_NAMESPACES:
            associations = read_gaf(gaf_filename, namespace=namespace, go2geneids=False, prt=None)
            assocs[namespace] = associations

        SPECIES_ASSOCIATIONS[species] = assocs
        print()
    return SPECIES_ASSOCIATIONS, GAF_NAME_TO_ID

# Gene ontology constants

BIOLOGICAL_PROCESS = 'BP'
CELLULAR_COMPONENT = 'CC'
MOLECULAR_FUNCTION = 'MF'
GO_NAMESPACES = [ BIOLOGICAL_PROCESS, CELLULAR_COMPONENT, MOLECULAR_FUNCTION ]


# default gene ontology files to download, see http://current.geneontology.org/products/pages/downloads.html
SPECIES_TO_GAF_PREFIX = {
    # ARABIDOPSIS_THALIANA: 'tair',
    # BOS_TAURUS: 'goa_cow',
    # CAENORHABDITIS_ELEGANS: 'wb',
    # CANIS_LUPUS_FAMILIARIS: 'goa_dog',
    DANIO_RERIO: 'zfin',
    # DICTYOSTELIUM_DISCOIDEUM: 'dictybase',
    # DROSOPHILA_MELANOGASTER: 'fb',
    # GALLUS_GALLUS: 'goa_chicken',
    # HOMO_SAPIENS: 'goa_human',
    # MUS_MUSCULUS: 'mgi',
    # ORYZA_SATIVA: 'gramene_oryza',
    # RATTUS_NORVEGICUS: 'rgd',
    # SACCHAROMYCES_CEREVISIAE: 'sgd',
    # SUS_SCROFA: 'goa_pig'
}

print('Loading Gene Ontologies (slim)')
# ONTOLOGIES_FILENAME = 'ontologies.p'
# ONTOLOGIES = load_obj(ONTOLOGIES_FILENAME)
# if ONTOLOGIES is None:
#     # download GO-slim if not found
#     ONTOLOGIES = download_ontologies()
#     save_obj(ONTOLOGIES, ONTOLOGIES_FILENAME)
ONTOLOGIES = download_ontologies()

print('\nLoading association data')
# ASSOCIATION_FILENAME = 'associations.p'
# ASSOCIATION_DATA = load_obj(ASSOCIATION_FILENAME)
# if ASSOCIATION_DATA is not None:
#     SPECIES_ASSOCIATIONS = ASSOCIATION_DATA['assoc']
#     GAF_NAME_TO_ID = ASSOCIATION_DATA['gafs']
# else:
#     # download association files for all species in SPECIES_TO_GAF_PREFIX
#     SPECIES_ASSOCIATIONS, GAF_NAME_TO_ID = download_associations()
#     ASSOCIATION_DATA = {
#         'assoc': SPECIES_ASSOCIATIONS,
#         'gafs': GAF_NAME_TO_ID
#     }
#     save_obj(ASSOCIATION_DATA, ASSOCIATION_FILENAME)
SPECIES_ASSOCIATIONS, GAF_NAME_TO_ID = download_associations()
