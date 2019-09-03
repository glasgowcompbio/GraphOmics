import pandas as pd
from goatools.associations import read_gaf
from goatools.base import dnld_gaf
from goatools.base import download_go_basic_obo
from goatools.obo_parser import GODag

from linker.constants import *
from tqdm import tqdm


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
    species_associations = {}
    gaf_name_to_id = {}
    for species, gaf_prefix in tqdm(SPECIES_TO_GAF_PREFIX.items()):

        gaf_filename = dnld_gaf(gaf_prefix, prt=None, loading_bar=False)
        gaf_name_to_id[species] = gaf_names_to_id(gaf_filename)

        assocs = {}
        for namespace in GO_NAMESPACES:
            associations = read_gaf(gaf_filename, namespace=namespace, go2geneids=False, prt=None)
            assocs[namespace] = associations

        species_associations[species] = assocs
    return species_associations, gaf_name_to_id
