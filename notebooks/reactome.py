from collections import defaultdict

from neo4j.v1 import GraphDatabase, basic_auth
from ipywidgets import FloatProgress


def ensembl_to_uniprot(ensembl_ids, species, show_progress_bar=False):

    results = {}
    try:

        driver = GraphDatabase.driver("bolt://localhost:7687", auth=basic_auth("neo4j", "neo4j"))
        session = driver.session()
        query = """
        MATCH
            (rg:ReferenceGeneProduct)-[:referenceGene]->(rs:ReferenceSequence)-[:species]->(s:Species)
        WHERE
            rs.identifier IN {ensembl_ids} AND
            s.displayName = {species}
        RETURN DISTINCT
            rs.identifier AS gene_id,
            rs.databaseName AS gene_db,
            rg.identifier AS protein_id,
            rg.databaseName AS protein_db,
            rg.url as URL
        """
        params = {
            'ensembl_ids': ensembl_ids,
            'species': species
        }
        query_res = session.run(query, params)

        if show_progress_bar:
            f = FloatProgress(min=0, max=len(ensembl_ids))
            display(f)

        results = defaultdict(list)
        i = 0
        for record in query_res:
            gene_id = record['gene_id']
            item = {'protein_id': record['protein_id'], 'url': record['URL']}
            results[gene_id].append(item)
            if show_progress_bar: f.value += 1
        f.value = len(ensembl_ids)

    except Exception as e:
        print e

    finally:
        session.close()

    return results

def uniprot_to_reaction(uniprot_ids, species, show_progress_bar=False):

    results = {}
    try:

        driver = GraphDatabase.driver("bolt://localhost:7687", auth=basic_auth("neo4j", "neo4j"))
        session = driver.session()
        query = """

        MATCH (rle:ReactionLikeEvent)-[:input|output|catalystActivity|physicalEntity
              |regulatedBy|regulator|hasComponent|hasMember|hasCandidate*]->(pe:PhysicalEntity),
              (pe)-[:referenceEntity]->(re:ReferenceEntity)-[:referenceDatabase]->(rd:ReferenceDatabase)
        WHERE
            re.identifier IN {uniprot_ids} AND
            rd.displayName = 'UniProt' AND
            rle.speciesName = {species}
        RETURN DISTINCT
            re.identifier AS protein_id,
            rd.displayName AS protein_db,
            rle.stId AS reaction_id,
            rle.displayName AS reaction_name
        """
        params = {
            'uniprot_ids': uniprot_ids,
            'species': species
        }
        query_res = session.run(query, params)

        if show_progress_bar:
            f = FloatProgress(min=0, max=len(uniprot_ids))
            display(f)

        results = defaultdict(list)
        i = 0
        for record in query_res:
            protein_id = record['protein_id']
            item = {'reaction_id': record['reaction_id'], 'reaction_name': record['reaction_name']}
            results[protein_id].append(item)
            if show_progress_bar: f.value += 1
        f.value = len(uniprot_ids)

    finally:
        session.close()

    return results