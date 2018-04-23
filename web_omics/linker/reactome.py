from collections import defaultdict
import time

from neo4j.v1 import GraphDatabase, basic_auth

import xmltodict
import pandas as pd
from bioservices.kegg import KEGG
from bioservices.reactome import Reactome


def get_species_list():

    results = []
    try:

        driver = GraphDatabase.driver("bolt://localhost:7687",
                                      auth=basic_auth("neo4j", "neo4j"))
        session = driver.session()
        query = """
        MATCH (n:Species) RETURN n.displayName AS name order by name        
        """
        query_res = session.run(query)
        for record in query_res:
            results.append(record['name'])

    except Exception as e:
        print(e)

    finally:
        session.close()

    return results


def get_species_dict():
    species_list = get_species_list()
    species_dict = {}
    for idx, s in enumerate(species_list):
        species_dict[idx] = s
    return species_dict


################################################################################
### Gene-related functions                                                   ###
################################################################################


def ensembl_to_uniprot(ensembl_ids, species):

    id_to_names = {}
    results = defaultdict(list)
    try:

        driver = GraphDatabase.driver("bolt://localhost:7687",
                                      auth=basic_auth("neo4j", "neo4j"))
        session = driver.session()
        query = """
        MATCH
            (rg:ReferenceGeneProduct)-[:referenceGene]->
            (rs:ReferenceSequence)-[:species]->(s:Species)
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

        results = defaultdict(list)
        for record in query_res:
            gene_id = record['gene_id']
            protein_id = record['protein_id']
            results[gene_id].append(protein_id)

    except Exception as e:
        print(e)

    finally:
        session.close()

    return dict(results), id_to_names


################################################################################
### Protein-related functions                                                ###
################################################################################


def uniprot_to_reaction(uniprot_ids, species):

    id_to_names = {}
    results = defaultdict(list)
    try:

        driver = GraphDatabase.driver("bolt://localhost:7687",
                                      auth=basic_auth("neo4j", "neo4j"))
        session = driver.session()

        # note that using hasComponent|hasMember|hasCandidate below will
        # retrieve all the sub-complexes too
        query = """
        MATCH (rle:ReactionLikeEvent)-[:input|output|catalystActivity
              |physicalEntity|regulatedBy|regulator|hasComponent|hasMember
              |hasCandidate*]->
              (pe:PhysicalEntity)-[:referenceEntity]->
              (re:ReferenceEntity)-[:referenceDatabase]->
              (rd:ReferenceDatabase)
        WHERE
            re.identifier IN {uniprot_ids} AND
            rd.displayName = 'UniProt' AND
            rle.speciesName = {species}
        RETURN DISTINCT
            re.identifier AS protein_id,
            re.description AS description,
            rd.displayName AS protein_db,
            rle.stId AS reaction_id,
            rle.displayName AS reaction_name
        """
        params = {
            'uniprot_ids': uniprot_ids,
            'species': species
        }
        query_res = session.run(query, params)

        results = defaultdict(list)
        for record in query_res:
            protein_id = record['protein_id']
            item = {
                'reaction_id': record['reaction_id'],
                'reaction_name': record['reaction_name']
            }
            results[protein_id].append(item)

    finally:
        session.close()

    return dict(results), id_to_names


################################################################################
### Compound-related functions                                               ###
################################################################################


def get_all_compound_ids():

    results = []
    try:

        driver = GraphDatabase.driver("bolt://localhost:7687",
                                      auth=basic_auth("neo4j", "neo4j"))
        session = driver.session()
        query = """
        MATCH (di:DatabaseIdentifier)
        WHERE
            di.databaseName = 'COMPOUND'
        RETURN DISTINCT
            di.displayName AS compound_id
        """
        query_res = session.run(query)
        for record in query_res:
            key = record['compound_id'].split(':')  # e.g. 'COMPOUND:C00025'
            compound_id = key[1]
            results.append(compound_id)

    finally:
        session.close()

    return results


def compound_to_reaction(compound_ids, species):

    id_to_names = {}
    results = defaultdict(list)
    try:

        driver = GraphDatabase.driver("bolt://localhost:7687",
                                      auth=basic_auth("neo4j", "neo4j"))
        session = driver.session()
        query = """
        MATCH (rle:ReactionLikeEvent)-[:input|output|catalystActivity
              |physicalEntity|regulatedBy|regulator|hasComponent|hasMember
              |hasCandidate*]->
              (pe:PhysicalEntity)-[:crossReference]->
              (di:DatabaseIdentifier)
        WHERE
            di.identifier IN {compound_ids} AND
            di.databaseName = 'COMPOUND' AND
            rle.speciesName = {species}
        RETURN DISTINCT
            di.displayName AS compound_id,
            di.databaseName AS compound_db,
            rle.stId AS reaction_id,
        	rle.displayName AS reaction_name
        """
        params = {
            'compound_ids': compound_ids,
            'species': species
        }
        query_res = session.run(query, params)

        for record in query_res:
            key = record['compound_id'].split(':')  # e.g. 'COMPOUND:C00025'
            compound_id = key[1]
            item = {
                'reaction_id': record['reaction_id'],
                'reaction_name': record['reaction_name']
            }
            results[compound_id].append(item)

    finally:
        session.close()

    return dict(results), id_to_names


def produce_kegg_dict(kegg_location, param):

    with open(kegg_location) as kegg_cmpd_file:
        cmpd_dict = xmltodict.parse(kegg_cmpd_file.read())

    kegg_dict = {}
    for compound in cmpd_dict['compounds']['compound']:
        kegg_dict[compound[param]] = compound['formula']

    return kegg_dict

################################################################################
### Reaction-related functions                                               ###
################################################################################


# get all the entities involved in a reaction
def get_reaction_entities(reaction_ids, species):

    results = defaultdict(list)
    try:

        driver = GraphDatabase.driver("bolt://localhost:7687",
                                      auth=basic_auth("neo4j", "neo4j"))
        session = driver.session()
        query = """
        MATCH (rle:ReactionLikeEvent)-[rr:input|output|catalystActivity
              |physicalEntity|regulatedBy|regulator|hasComponent|hasMember
              |hasCandidate*]->(dbo:DatabaseObject)
        WHERE
            rle.stId IN {reaction_ids} AND
            rle.speciesName = {species}
        RETURN
            rle.stId AS reaction_id,
            dbo.stId AS entity_id,
            dbo.schemaClass AS schema_class,
            dbo.displayName as display_name,
            extract(rel IN rr | type(rel)) AS types
        """
        params = {
            'reaction_ids': reaction_ids,
            'species': species
        }
        query_res = session.run(query, params)
        for record in query_res:
            reaction_id = record['reaction_id']
            entity_id = record['entity_id']
            schema_class = record['schema_class']
            display_name = record['display_name']
            relationship_types = record['types']
            item = (schema_class, entity_id, display_name, relationship_types)
            results[reaction_id].append(item)

    finally:
        session.close()

    return results


def reaction_to_metabolite_pathway(reaction_ids, species,
                                   leaf=True):

    id_to_names = {}
    results = defaultdict(list)
    try:

        driver = GraphDatabase.driver("bolt://localhost:7687",
                                      auth=basic_auth("neo4j", "neo4j"))
        session = driver.session()

        if leaf:
            # retrieve only the leaf nodes in the pathway hierarchy
            query = """
            MATCH (tp:TopLevelPathway)-[:hasEvent*]->
                  (p:Pathway)-[:hasEvent*]->(rle:ReactionLikeEvent)
            WHERE
            	tp.displayName = 'Metabolism' AND
                tp.speciesName = {species} AND
            	rle.stId IN {reaction_ids} AND
                (p)-[:hasEvent]->(rle)
            RETURN
                rle.stId AS reaction_id,
        	    rle.displayName AS reaction_name,
                p.stId AS pathway_id,
                p.displayName AS pathway_name
            """
        else:
            # retrieve all nodes maps reactions to all levels in the pathway
            # hierarchy (except the top-level)
            query = """
            MATCH (tp:TopLevelPathway)-[:hasEvent*]->
                  (p:Pathway)-[:hasEvent*]->(rle:ReactionLikeEvent)
            WHERE
            	tp.displayName = 'Metabolism' AND
                tp.speciesName = {species} AND
            	rle.stId IN {reaction_ids}
            RETURN
                rle.stId AS reaction_id,
        	    rle.displayName AS reaction_name,
                p.stId AS pathway_id,
                p.displayName AS pathway_name
            """
        params = {
            'reaction_ids': reaction_ids,
            'species': species
        }
        query_res = session.run(query, params)

        for record in query_res:
            reaction_id = record['reaction_id']
            reaction_name = record['reaction_name']
            pathway_id = record['pathway_id']
            pathway_name = record['pathway_name']
            item = {
                'pathway_id': pathway_id,
                'pathway_name': pathway_name
            }
            results[reaction_id].append(item)
            id_to_names[reaction_id] = reaction_name
            id_to_names[pathway_id] = pathway_name

    finally:
        session.close()

    return dict(results), id_to_names

################################################################################
### Pathway-related functions                                                ###
################################################################################


# def get_metabolite_pathways(reaction_ids, species,
#                             show_progress_bar=False,
#                             leaf=True):

def retrieve_kegg_formula(reactome_compound_name):
    k = KEGG()
    compound_name = reactome_compound_name.replace('COMPOUND', 'cpd')
    res = k.get(compound_name).split('\n')
    for line in res:
        if line.startswith('FORMULA'):
            formula = line.split()[1]  # get the second token
            return formula
    return None


def get_all_pathways_formulae(species):

    results = defaultdict(set)
    pathway_id_to_name = {}
    try:

        driver = GraphDatabase.driver("bolt://localhost:7687",
                                      auth=basic_auth("neo4j", "neo4j"))
        session = driver.session()

        # TODO: retrieve only the leaf nodes in the pathway hierarchy
        query = """
        MATCH (tp:TopLevelPathway)-[:hasEvent*]->
              (p:Pathway)-[:hasEvent*]->(rle:ReactionLikeEvent),
              (rle)-[:input|output|catalystActivity|physicalEntity|regulatedBy|regulator|hasComponent
              |hasMember|hasCandidate*]->(pe:PhysicalEntity),
              (pe:PhysicalEntity)-[:crossReference]->(di:DatabaseIdentifier)<-[:crossReference]-(rm:ReferenceMolecule)
        WHERE
              tp.displayName = 'Metabolism' AND
              tp.speciesName = {species} AND
              di.databaseName = 'COMPOUND' AND
              (p)-[:hasEvent]->(rle)
        RETURN DISTINCT
            p.schemaClass,
            p.displayName AS pathway_name,
            p.stId AS pathway_id,
            di.displayName as compound_name,
            rm.formula AS formula,
            di.url
        """
        params = {
            'species': species
        }
        query_res = session.run(query, params)

        i = 0
        retrieved = {}
        for record in query_res:
            pathway_id = record['pathway_id']
            pathway_name = record['pathway_name']
            pathway_id_to_name[pathway_id] = pathway_name
            compound_name = record['compound_name']
            formula = record['formula']
            if formula is None:
                if compound_name not in retrieved:
                    formula = retrieve_kegg_formula(compound_name)
                    print('Missing formula for %s, retrieved %s from kegg' %
                          (compound_name, formula))
                    retrieved[compound_name] = formula
                else:
                    formula = retrieved[compound_name]
            assert formula is not None, 'Formula is missing for %s' % compound_name
            results[pathway_id].add(formula)

    finally:
        session.close()

    return dict(results), pathway_id_to_name

################################################################################
### Analysis functions                                                       ###
################################################################################


def get_reaction_ids(mapping):
    all_reactions = []
    for key in mapping:
        rs = mapping[key]
        rids = [r['reaction_id'] for r in rs]
        all_reactions.extend(rids)
    return all_reactions


def get_reactions_from_mapping(mapping):
    reaction_names = {}
    reaction_members = defaultdict(list)
    for key in mapping:
        for reaction in mapping[key]:
            r_id = reaction['reaction_id']
            r_name = reaction['reaction_name']
            reaction_names[r_id] = r_name
            reaction_members[r_id].append(key)
    assert reaction_names.keys() == reaction_members.keys()
    return reaction_names, dict(reaction_members)


def get_protein_to_gene(mapping):
    protein_to_gene = defaultdict(list)
    for gene_id in mapping:
        for protein_id in mapping[gene_id]:
            protein_to_gene[protein_id].append(gene_id)
    return dict(protein_to_gene)


def merge_two_dicts(x, y):
    # https://stackoverflow.com/questions/38987/how-to-merge-two-dictionaries-in-a-single-expression
    z = x.copy()   # start with x's keys and values
    z.update(y)    # modifies z with y's keys and values & returns None
    return z


def get_coverage(observed_count, total_count):
    try:
        return observed_count / float(total_count)
    except ZeroDivisionError:
        return 0


def get_reaction_df(transcript_mapping, protein_mapping, compound_mapping,
                    pathway_mapping, species):

    r_name_1, r_members_1 = get_reactions_from_mapping(protein_mapping)
    r_name_2, r_members_2 = get_reactions_from_mapping(compound_mapping)
    reaction_names = merge_two_dicts(r_name_1, r_name_2)
    protein_to_gene = get_protein_to_gene(transcript_mapping)

    reaction_ids = set(list(r_members_1.keys()) + list(r_members_2.keys()))
    reaction_entities = get_reaction_entities(list(reaction_ids), species)
    rows = []
    for reaction_id in reaction_ids:

        observed_protein_count = 0
        observed_compound_count = 0
        protein_str = ''
        compound_str = ''

        if reaction_id in r_members_1:
            proteins = r_members_1[reaction_id]
            observed_protein_count = len(proteins)
            for prot in proteins:
                if prot in protein_to_gene:
                    protein_str += '%s (%s):' % (prot, ':'.join(
                        protein_to_gene[prot]))
                else:
                    protein_str += '%s:' % prot
            protein_str = protein_str.rstrip(':')  # remove last :

        if reaction_id in r_members_2:
            compounds = r_members_2[reaction_id]
            observed_compound_count = len(compounds)
            compound_str = ':'.join(compounds)

        entities = reaction_entities[reaction_id]
        all_compound_count = len([x for x in entities
                                  if x[0] == 'SimpleEntity'])
        all_protein_count = len([x for x in entities
                                 if x[0] == 'EntityWithAccessionedSequence'])

        reaction_name = reaction_names[reaction_id]
        protein_coverage = get_coverage(observed_protein_count,
                                        all_protein_count)
        compound_coverage = get_coverage(observed_compound_count,
                                         all_compound_count)
        s1 = observed_protein_count + observed_compound_count
        s2 = all_protein_count + all_compound_count
        all_coverage = get_coverage(s1, s2)

        if reaction_id in pathway_mapping:
            pathway_id_str = ':'.join([x['pathway_id']
                                       for x in pathway_mapping[reaction_id]])
            pathway_name_str = ':'.join([x['pathway_name']
                                         for x in pathway_mapping[reaction_id]])
            protein_coverage_str = '%.2f' % protein_coverage
            compound_coverage_str = '%.2f' % compound_coverage
            all_coverage_str = '%.2f' % all_coverage
            row = (reaction_id,
                   reaction_name,
                   protein_coverage_str,
                   compound_coverage_str,
                   all_coverage_str,
                   protein_str,
                   observed_protein_count,
                   all_protein_count,
                   compound_str,
                   observed_compound_count,
                   all_compound_count,
                   pathway_id_str,
                   pathway_name_str)
            rows.append(row)

    df = pd.DataFrame(rows, columns=['reaction_id',
                                     'reaction_name',
                                     'protein_coverage',
                                     'compound_coverage',
                                     'all_coverage',
                                     'protein',
                                     'observed_protein_count',
                                     'all_protein_count',
                                     'compound',
                                     'observed_compound_count',
                                     'all_compound_count',
                                     'pathway_ids',
                                     'pathway_names'])
    return df
