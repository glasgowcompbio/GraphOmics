#!/usr/bin/env python
import os
import re
import shutil
import sys
from pathlib import Path

from tqdm import tqdm

sys.path.append('linker')

from reactome import get_all_compound_ids
from metadata import get_compound_metadata_online
from common import save_obj, download_file, extract_zip_file
from GTF import lines
from gene_ontologies_utils import download_ontologies, download_associations


def kegg_id_to_display_names():
    compound_ids = get_all_compound_ids()
    metadata = get_compound_metadata_online(compound_ids)
    outfile = os.path.join(os.getcwd(), 'static', 'data', 'compound_names.p')
    save_obj(metadata, outfile)


def kegg_id_to_chebi_id():
    # TODO: replace with the actual owl file from https://www.ebi.ac.uk/chebi/downloadsForward.do
    url = 'https://www.dropbox.com/s/k002aymluhcvcxe/chebi.zip?dl=1'

    zip_file = 'chebi.zip'
    extracted_file = 'chebi.owl'
    if not os.path.exists(zip_file):
        download_file(url, zip_file)
    extract_zip_file(zip_file)

    kegg_to_chebi_lines = {}
    with open(extracted_file, encoding='utf-8') as f:
        for line in f:
            if 'owl:Class' in line and 'rdf:about' in line:
                chebi_line = line
            if 'oboInOwl:hasDbXref' in line and 'KEGG:C' in line:
                kegg_line = line
                kegg_to_chebi_lines[kegg_line.strip()] = chebi_line.strip()

    kegg_to_chebi = {}
    for k, v in kegg_to_chebi_lines.items():
        res = re.search('>KEGG:(.*)<', k)
        kegg = res.group(1)
        res = re.search('CHEBI_(.*)"', v)
        chebi = res.group(1)
        kegg_to_chebi[kegg] = chebi

    outfile = os.path.join(os.getcwd(), 'static', 'data', 'kegg_to_chebi.p')
    save_obj(kegg_to_chebi, outfile)
    os.remove(extracted_file)


def parse_gtf():
    # TODO: get all the files using
    #      wget -r ftp://ftp.ensembl.org/pub/release-97/gtf
    url = 'https://www.dropbox.com/s/kar64i2z4lao5y6/gtf.zip?dl=1'

    zip_file = os.path.join(os.getcwd(), 'gtf.zip')
    if not os.path.exists(zip_file):
        download_file(url, zip_file)
    extract_zip_file(zip_file)

    gene_names = {}
    filenames = [str(x) for x in Path('gtf').glob('**/*.gtf.gz')]
    for filename in tqdm(filenames):
        try:
            gtf_dict = lines(str(filename))
            for d in gtf_dict:
                try:
                    gene_id = d['gene_id']
                    gene_name = d['gene_name']
                    gene_names[gene_id] = gene_name
                except KeyError:
                    continue
        except IndexError:
            continue

    save_obj(gene_names, os.path.join(os.getcwd(), 'static', 'data', 'gene_names.p'))
    shutil.rmtree('gtf')


def download_go():
    ontologies = download_ontologies()
    species_associations, gaf_name_to_id = download_associations()
    go_data = {
        'ontologies': ontologies,
        'species_associations': species_associations,
        'gaf_name_to_id': gaf_name_to_id
    }

    # we need to do this because ontology terms are recursive, with parents/children relationships
    sys.setrecursionlimit(100000)
    save_obj(go_data, os.path.join(os.getcwd(), 'static', 'data', 'go_data.p'))
    delete_by_pattern('*.obo')
    delete_by_pattern('*.gaf')


def delete_by_pattern(extension):
    for p in Path('.').glob(extension):
        p.unlink()


if __name__ == '__main__':
    # Create the mapping between KEGG to display names, see notebooks/mapping/get_all_compounds.ipynb
    print('\n---------------------------------------------------')
    print('1/4 Exporting KEGG -> display names')
    print('---------------------------------------------------')
    kegg_id_to_display_names()

    # Create a mapping between KEGG ID to ChEBI ID, see notebooks/mapping/kegg_to_chebi.ipynb
    print('\n---------------------------------------------------')
    print('2/4 Exporting KEGG -> ChEBI mapping')
    print('---------------------------------------------------')
    kegg_id_to_chebi_id()

    # Create a mapping between Ensemble gene ID to gene names, see notebooks/mapping/parse_gtf.ipynb
    print('\n---------------------------------------------------')
    print('3/4 Exporting gene ID -> gene name')
    print('---------------------------------------------------')
    parse_gtf()

    # Download gene ontology and association files
    print('\n---------------------------------------------------')
    print('4/4 Downloading gene ontology and association files')
    print('---------------------------------------------------')
    download_go()

