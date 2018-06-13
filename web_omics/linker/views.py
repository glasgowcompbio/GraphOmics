import json
import urllib.request
from urllib.parse import urlparse
from io import StringIO
import collections

import pandas as pd
import wikipedia

from django.http import HttpResponse
from django.http import JsonResponse
from django.shortcuts import render
from django.templatetags.static import static
from django.views.generic.edit import FormView
from django.shortcuts import render, get_object_or_404

from linker.forms import LinkerForm
from linker.models import Analysis

from linker.metadata import get_compound_metadata
from linker.metadata import get_single_ensembl_metadata_online, get_single_uniprot_metadata_online, \
    get_single_compound_metadata_online, clean_label, get_gene_names, kegg_to_chebi
from linker.reactome import ensembl_to_uniprot, uniprot_to_ensembl, uniprot_to_reaction, compound_to_reaction, \
    get_species_dict, get_reactome_description
from linker.reactome import reaction_to_metabolite_pathway, get_reaction_entities, reaction_to_compound, \
    reaction_to_uniprot, pathway_to_reactions, get_reaction_df

Relation = collections.namedtuple('Relation', 'keys values mapping_list')
NA = '-'  # this should be something that will appear first in the table when sorted alphabetically

TRUNCATE_LIMIT = 400

GENE_PK = 'gene_pk'
PROTEIN_PK = 'protein_pk'
COMPOUND_PK = 'compound_pk'
REACTION_PK = 'reaction_pk'
PATHWAY_PK = 'pathway_pk'


def explore_data(request, analysis_id):
    analysis = get_object_or_404(Analysis, pk=analysis_id)
    data = {
        'genes_json': json.dumps(analysis.genes_json),
        'proteins_json': json.dumps(analysis.proteins_json),
        'compounds_json': json.dumps(analysis.compounds_json),
        'reactions_json': json.dumps(analysis.reactions_json),
        'pathways_json': json.dumps(analysis.pathways_json),
        'gene_proteins_json': json.dumps(analysis.gene_proteins_json),
        'protein_reactions_json': json.dumps(analysis.protein_reactions_json),
        'compound_reactions_json': json.dumps(analysis.compound_reactions_json),
        'reaction_pathways_json': json.dumps(analysis.reaction_pathways_json),
        'species': analysis.species,
    }
    context = {
        'data': data,
        'analysis_id': analysis.pk,
        'analysis_name': analysis.name,
        'analysis_description': analysis.description
    }
    return render(request, 'linker/explore_data.html', context)


def inference(request, analysis_id):
    analysis = get_object_or_404(Analysis, pk=analysis_id)
    context = {
        'analysis_id': analysis.pk
    }
    return render(request, 'linker/inference.html', context)


def settings(request, analysis_id):
    analysis = get_object_or_404(Analysis, pk=analysis_id)
    context = {
        'analysis_id': analysis.pk
    }
    return render(request, 'linker/settings.html', context)


class CreateAnalysisView(FormView):
    template_name = 'linker/create_analysis.html'
    form_class = LinkerForm
    success_url = 'linker/explore_data.html'

    def form_valid(self, form):
        genes_str = form.cleaned_data['genes']
        proteins_str = form.cleaned_data['proteins']
        compounds_str = form.cleaned_data['compounds']
        species_key = int(form.cleaned_data['species'])
        species_dict = get_species_dict()
        species = species_dict[species_key]

        ### all the ids that we have from the user ###
        
        observed_gene_df = csv_to_dataframe(genes_str)
        observed_protein_df = csv_to_dataframe(proteins_str)
        observed_compound_df = csv_to_dataframe(compounds_str)
        observed_gene_ids = get_ids_from_dataframe(observed_gene_df)
        observed_protein_ids = get_ids_from_dataframe(observed_protein_df)

        # try to convert all kegg ids to chebi ids, if possible
        observed_compound_ids = get_ids_from_dataframe(observed_compound_df)
        kegg_2_chebi = kegg_to_chebi(observed_compound_ids)
        observed_compound_df.iloc[:, 0] = observed_compound_df.iloc[:, 0].map(kegg_2_chebi) # assume 1st column is id
        observed_compound_ids = get_ids_from_dataframe(observed_compound_df)

        ### map genes -> proteins ###

        gene_2_proteins_mapping, _ = ensembl_to_uniprot(observed_gene_ids, species)
        gene_2_proteins = make_relations(gene_2_proteins_mapping, GENE_PK, PROTEIN_PK, value_key=None)

        ### maps proteins -> reactions ###

        protein_ids_from_genes = gene_2_proteins.values
        known_protein_ids = list(set(observed_protein_ids + protein_ids_from_genes))
        protein_2_reactions_mapping, _ = uniprot_to_reaction(known_protein_ids, species)
        protein_2_reactions = make_relations(protein_2_reactions_mapping, PROTEIN_PK, REACTION_PK, value_key='reaction_id')

        ### maps compounds -> reactions ###

        compound_2_reactions_mapping, _ = compound_to_reaction(observed_compound_ids, species)
        compound_2_reactions = make_relations(compound_2_reactions_mapping, COMPOUND_PK, REACTION_PK, value_key='reaction_id')

        ### maps reactions -> metabolite pathways ###

        reaction_ids_from_proteins = protein_2_reactions.values
        reaction_ids_from_compounds = compound_2_reactions.values
        reaction_ids = list(set(reaction_ids_from_proteins + reaction_ids_from_compounds))
        reaction_2_pathways_mapping, reaction_2_pathways_id_to_names = reaction_to_metabolite_pathway(reaction_ids, species)
        reaction_2_pathways = make_relations(reaction_2_pathways_mapping, REACTION_PK, PATHWAY_PK, value_key='pathway_id')
        reaction_ids = reaction_2_pathways.keys # keep only reactions in metabolic pathways

        ### maps reactions -> proteins ###

        mapping, _ = reaction_to_uniprot(reaction_ids, species)
        reaction_2_proteins = make_relations(mapping, REACTION_PK, PROTEIN_PK, value_key=None)
        protein_2_reactions = reverse(reaction_2_proteins)
        protein_ids = protein_2_reactions.keys

        ### maps reactions -> compounds ###

        reaction_2_compounds_mapping, reaction_to_compound_id_to_names = reaction_to_compound(reaction_ids, species)
        reaction_2_compounds = make_relations(reaction_2_compounds_mapping, REACTION_PK, COMPOUND_PK, value_key=None)
        compound_2_reactions = reverse(reaction_2_compounds)
        compound_ids = compound_2_reactions.keys

        ### map proteins -> genes ###

        mapping, _ = uniprot_to_ensembl(protein_ids, species)
        protein_2_genes = make_relations(mapping, PROTEIN_PK, GENE_PK, value_key=None)
        gene_2_proteins = merge(gene_2_proteins, reverse(protein_2_genes))
        inferred_gene_ids = protein_2_genes.values
        gene_ids = list(set(observed_gene_ids + inferred_gene_ids))

        ### add links ###

        # map NA to NA
        gene_2_proteins = add_links(gene_2_proteins, GENE_PK, PROTEIN_PK, [NA], [NA])
        protein_2_reactions = add_links(protein_2_reactions, PROTEIN_PK, REACTION_PK, [NA], [NA])
        compound_2_reactions = add_links(compound_2_reactions, COMPOUND_PK, REACTION_PK, [NA], [NA])
        reaction_2_pathways = add_links(reaction_2_pathways, REACTION_PK, PATHWAY_PK, [NA], [NA])

        # map genes that have no proteins to NA
        gene_pk_list = [x for x in gene_ids if x not in gene_2_proteins.keys]
        gene_2_proteins = add_links(gene_2_proteins, GENE_PK, PROTEIN_PK, gene_pk_list, [NA])

        # map proteins that have no genes to NA
        protein_pk_list = [x for x in protein_ids if x not in gene_2_proteins.values]
        gene_2_proteins = add_links(gene_2_proteins, GENE_PK, PROTEIN_PK, [NA], protein_pk_list)

        # map proteins that have no reactions to NA
        protein_pk_list = [x for x in protein_ids if x not in protein_2_reactions.keys]
        protein_2_reactions = add_links(protein_2_reactions, PROTEIN_PK, REACTION_PK, protein_pk_list, [NA])

        # map reactions that have no proteins to NA
        reaction_pk_list = [x for x in reaction_ids if x not in protein_2_reactions.values]
        protein_2_reactions = add_links(protein_2_reactions, PROTEIN_PK, REACTION_PK, [NA], reaction_pk_list)

        # map compounds that have no reactions to NA
        compound_pk_list = [x for x in compound_ids if x not in compound_2_reactions.keys]
        compound_2_reactions = add_links(compound_2_reactions, COMPOUND_PK, REACTION_PK, compound_pk_list, [NA])

        # map reactions that have no compounds to NA
        reaction_pk_list = [x for x in reaction_ids if x not in compound_2_reactions.values]
        compound_2_reactions = add_links(compound_2_reactions, COMPOUND_PK, REACTION_PK, [NA], reaction_pk_list)

        # map reactions that have no pathways to NA
        reaction_pk_list = [x for x in reaction_ids if x not in reaction_2_pathways.keys]
        reaction_2_pathways = add_links(reaction_2_pathways, REACTION_PK, PATHWAY_PK, reaction_pk_list, [NA])

        ### set everything to the request context ###

        gene_2_proteins_json = json.dumps(gene_2_proteins.mapping_list)
        protein_2_reactions_json = json.dumps(protein_2_reactions.mapping_list)
        compound_2_reactions_json = json.dumps(compound_2_reactions.mapping_list)
        reaction_2_pathways_json = json.dumps(reaction_2_pathways.mapping_list)

        rel_path = static('data/gene_names.p')
        pickled_url = self.request.build_absolute_uri(rel_path)
        metadata_map = get_gene_names(gene_ids, pickled_url)
        genes_json = pk_to_json(GENE_PK, 'gene_id', gene_ids, metadata_map, observed_gene_df)

        # metadata_map = get_uniprot_metadata_online(uniprot_ids)
        proteins_json = pk_to_json('protein_pk', 'protein_id', protein_ids, metadata_map, observed_protein_df)

        rel_path = static('data/compound_names.json')
        json_url = self.request.build_absolute_uri(rel_path)
        metadata_map = get_compound_metadata(compound_ids, json_url, reaction_to_compound_id_to_names)
        compounds_json = pk_to_json('compound_pk', 'compound_id', compound_ids, metadata_map, observed_compound_df)

        metadata_map = {}
        for name in reaction_2_pathways_id_to_names:
            tok = reaction_2_pathways_id_to_names[name]
            filtered = clean_label(tok)
            metadata_map[name] = {'display_name': filtered}

        reaction_count_df, pathway_count_df = get_count_df(gene_2_proteins_mapping, protein_2_reactions_mapping,
                                                           compound_2_reactions_mapping, reaction_2_pathways_mapping,
                                                           species)
        pathway_ids = reaction_2_pathways.values
        reactions_json = pk_to_json('reaction_pk', 'reaction_id', reaction_ids, metadata_map, reaction_count_df)
        pathways_json = pk_to_json('pathway_pk', 'pathway_id', pathway_ids, metadata_map, pathway_count_df)

        data = {
            'genes_json': genes_json,
            'proteins_json': proteins_json,
            'compounds_json': compounds_json,
            'reactions_json': reactions_json,
            'pathways_json': pathways_json,
            'gene_proteins_json': gene_2_proteins_json,
            'protein_reactions_json': protein_2_reactions_json,
            'compound_reactions_json': compound_2_reactions_json,
            'reaction_pathways_json': reaction_2_pathways_json,
            'species': species
        }
        context = {'data': data}

        analysis_name = form.cleaned_data['analysis_name']
        analysis_desc = form.cleaned_data['analysis_description']
        analysis = Analysis.objects.create(name=analysis_name,
                                  description=analysis_desc,
                                  species=species,
                                  genes_json=json.loads(genes_json),
                                  proteins_json=json.loads(proteins_json),
                                  compounds_json=json.loads(compounds_json),
                                  reactions_json=json.loads(reactions_json),
                                  pathways_json=json.loads(pathways_json),
                                  gene_proteins_json=json.loads(gene_2_proteins_json),
                                  protein_reactions_json=json.loads(protein_2_reactions_json),
                                  compound_reactions_json=json.loads(compound_2_reactions_json),
                                  reaction_pathways_json=json.loads(reaction_2_pathways_json))
        analysis.save()
        context['analysis_id'] = analysis.pk

        for k, v in data.items():
            save_json_string(v, 'static/data/debugging/' + k + '.json')

        return render(self.request, self.success_url, context)


def get_count_df(gene_2_proteins_mapping, protein_2_reactions_mapping, compound_2_reactions_mapping,
                 reaction_2_pathways_mapping, species):

    count_df, pathway_compound_counts, pathway_protein_counts = get_reaction_df(
        gene_2_proteins_mapping,
        protein_2_reactions_mapping,
        compound_2_reactions_mapping,
        reaction_2_pathways_mapping,
        species)

    reaction_count_df = count_df.rename({
        'reaction_id': 'reaction_pk',
        'observed_protein_count': 'R_E',
        'observed_compound_count': 'R_C'
    }, axis='columns')

    reaction_count_df = reaction_count_df.drop([
        'reaction_name',
        'protein_coverage',
        'compound_coverage',
        'all_coverage',
        'protein',
        'all_protein_count',
        'compound',
        'all_compound_count',
        'pathway_ids',
        'pathway_names'
    ], axis=1)

    pathway_pks = set(list(pathway_compound_counts.keys()) + list(pathway_protein_counts.keys()))
    data = []
    for pathway_pk in pathway_pks:
        try:
            p_e = pathway_protein_counts[pathway_pk]
        except KeyError:
            p_e = 0
        try:
            p_c = pathway_compound_counts[pathway_pk]
        except KeyError:
            p_c = 0
        data.append((pathway_pk, p_e, p_c))
    pathway_count_df = pd.DataFrame(data, columns=['pathway_pk', 'P_E', 'P_C'])

    return reaction_count_df, pathway_count_df


def save_json_string(data, outfile):
    with open(outfile, 'w') as f:
        f.write(data)
        print(outfile + ' saved')


def csv_to_dataframe(csv_str):
    data = StringIO(csv_str)
    try:
        df = pd.read_csv(data)
    except pd.errors.EmptyDataError:
        df = None
    return df


def get_ids_from_dataframe(df):
    if df is None:
        return []
    else:
        return df.values[:, 0].tolist() # id is always the first column


def merge(r1, r2):
    unique_keys = list(set(r1.keys + r2.keys))
    unique_values = list(set(r1.values + r2.values))
    mapping_list = r1.mapping_list + r2.mapping_list
    mapping_list = list(map(dict, set(map(lambda x: frozenset(x.items()), mapping_list)))) # removes duplicates, if any
    return Relation(keys=list(unique_keys), values=list(unique_values),
                    mapping_list=mapping_list)


def reverse(rel):
    return Relation(keys=rel.values, values=rel.keys, mapping_list=rel.mapping_list)


def pk_to_json(pk_label, display_label, data, metadata_map, observed_df):

    # turn the first column of the dataframe into index
    if observed_df is not None:
        observed_df = observed_df.set_index(observed_df.columns[0])
        observed_df = observed_df[~observed_df.index.duplicated(keep='first')] # remove row with duplicate indices
        observed_df = observed_df.fillna(value=0) # replace all NaNs with 0s

    output = []
    for item in sorted(data):

        if item == NA:
            continue # handled below after this loop

        # add primary key to row data
        row = {pk_label: item}

        # add display label to row_data
        if len(metadata_map) > 0 and item in metadata_map and metadata_map[item] is not None:
            label = metadata_map[item]['display_name']
        else:
            label = item
        row[display_label] = label

        # add the remaining data columns to row
        if observed_df is not None:
            try:
                data = observed_df.loc[item].to_dict()
            except KeyError: # missing data
                data = {}
                for col in observed_df.columns:
                    data.update({col: 0})
            row.update(data)

        output.append(row)

    # add dummy entry
    row = {pk_label: NA, display_label: NA}
    if observed_df is not None: # and the the values of the remaining columns for the dummy entry
        for col in observed_df.columns:
            row.update({col: 0})
    output.append(row)

    output_json = json.dumps(output)
    return output_json


def make_relations(mapping, source_pk, target_pk, value_key=None):
    id_values = []
    mapping_list = []

    for key in mapping:
        value_list = mapping[key]

        # value_list can be either a list of strings or dictionaries
        # check if the first element is a dict, else assume it's a string
        assert len(value_list) > 0
        is_string = True
        first = value_list[0]
        if isinstance(first, dict):
            is_string = False

        # process each element in value_list
        for value in value_list:
            if is_string:  # value_list is a list of string
                actual_value = value
            else:  # value_list is a list of dicts
                assert value_key is not None, 'value_key is missing'
                actual_value = value[value_key]
            id_values.append(actual_value)
            row = {source_pk: key, target_pk: actual_value}
            mapping_list.append(row)

    unique_keys = set(mapping.keys())
    unique_values = set(id_values)

    return Relation(keys=list(unique_keys), values=list(unique_values),
                    mapping_list=mapping_list)


def add_dummy(relation, source_ids, target_ids, source_pk_label, target_pk_label):

    to_add = [x for x in source_ids if x not in relation.keys]
    relation = add_links(relation, source_pk_label, target_pk_label, to_add, [NA])

    # to_add = [x for x in target_ids if x not in relation.values]
    # relation = add_links(relation, source_pk_label, target_pk_label, [NA], to_add)

    # relation = add_links(relation, source_pk_label, target_pk_label, [NA], [NA])
    return relation


def add_links(relation, source_pk_label, target_pk_label, source_pk_list, target_pk_list):

    rel_mapping_list = list(relation.mapping_list)
    rel_keys = relation.keys
    rel_values = relation.values

    for s1 in source_pk_list:
        if s1 not in rel_keys: rel_keys.append(s1)
        for s2 in target_pk_list:
            rel_mapping_list.append({source_pk_label: s1, target_pk_label: s2})
            if s2 not in rel_keys: rel_values.append(s2)

    return Relation(keys=rel_keys, values=rel_values, mapping_list=rel_mapping_list)


def get_ensembl_gene_info(request):
    if request.is_ajax():
        ensembl_id = request.GET['id']
        metadata = get_single_ensembl_metadata_online(ensembl_id)

        infos = []
        # selected = ['description', 'species', 'biotype', 'db_type', 'logic_name', 'strand', 'start', 'end']
        selected = ['description', 'species']
        for key in selected:
            value = metadata[key]
            if key == 'description':
                value = value[0:value.index('[')] # remove e.g. '[xxx]' from 'abhydrolase [xxx]'
            infos.append({'key': key.title(), 'value': value})

        display_name = metadata['display_name']
        try:
            summary = wikipedia.summary(display_name)
            if 'gene' in summary.lower() or 'protein' in summary.lower():
                infos.append({'key': 'Summary', 'value': truncate(summary)})
        except wikipedia.exceptions.DisambiguationError:
            pass
        except ValueError:
            pass

        images = []
        links = [
            {
                'text': 'Link to Ensembl',
                'href': 'https://www.ensembl.org/id/' + ensembl_id
            },
            {
                'text': 'Link to GeneCard',
                'href': 'https://www.genecards.org/cgi-bin/carddisp.pl?gene=' + display_name
            }
        ]
        # for x in metadata['Transcript']:
        #     text = 'Transcript: ' + x['display_name']
        #     href = 'https://www.ensembl.org/id/' + x['id']
        #     links.append({'text': text, 'href': href})

        data = {
            'infos': infos,
            'images': images,
            'links': links
        }
        return JsonResponse(data)


def get_uniprot_protein_info(request):
    if request.is_ajax():
        uniprot_id = request.GET['id']
        metadata = get_single_uniprot_metadata_online(uniprot_id)

        infos = []
        try:
            fullname = [x.text for x in metadata.soup.select('protein > recommendedname > fullname')][0]
        except IndexError:
            fullname = uniprot_id

        shortName = None
        try:
            shortname = [x.text for x in metadata.soup.select('protein > recommendedname > shortname')][0]
        except IndexError:
            pass

        if shortName is not None:
            infos.append({'key': 'Name', 'value': "{} ({})".format(fullname, shortname) })
        else:
            infos.append({'key': 'Name', 'value': "{}".format(fullname) })

        try:
            ecnumber = [x.text for x in metadata.soup.select('protein > recommendedname > ecnumber')][0]
            infos.append({'key': 'EC Number', 'value': 'EC' + ecnumber })
        except IndexError:
            pass

        # get comments
        selected = ['function', 'catalytic activity', 'enzyme regulation', 'subunit', 'pathway', 'miscellaneous', 'domain']
        for child in metadata.soup.find_all('comment'):
            try:
                if child['type'] in selected:
                    key = child['type'].title()
                    if key == 'Function': # quick-hack
                        key = 'Summary'
                    infos.append({'key': key, 'value': truncate(child.text)})
            except KeyError:
                continue

        # gene ontologies
        go = []
        for child in metadata.soup.find_all('dbreference'):
            try:
                if child['type'] == 'GO':
                    props = child.find_all('property')
                    for prop in props:
                        if prop['type'] == 'term':
                            go.append(prop['value'].split(':')[1])
            except KeyError:
                continue
        go_str = '; '.join(sorted(go))
        go_str = truncate(go_str)
        infos.append({'key': 'Gene_ontologies', 'value': go_str})

        images = []
        # with urllib.request.urlopen('https://swissmodel.expasy.org/repository/uniprot/' + uniprot_id + '.json') as url:
        #     data = json.loads(url.read().decode())
        #     for struct in data['result']['structures']:
        #         pdb_link = struct['coordinates']
        #         images.append(pdb_link)

        links = [
            {
                'text': 'Link to UniProt',
                'href': 'http://www.uniprot.org/uniprot/' + uniprot_id
            },
            {
                'text': 'Link to SWISS-MODEL',
                'href': 'https://swissmodel.expasy.org/repository/uniprot/' + uniprot_id
            }
        ]
        data = {
            'infos': infos,
            'images': images,
            'links': links
        }
        return JsonResponse(data)


def get_swissmodel_protein_pdb(request):
    pdb_url = request.GET['pdb_url']
    with urllib.request.urlopen(pdb_url) as response:
        content = response.read()
        return HttpResponse(content, content_type="text/plain")


def get_kegg_metabolite_info(request):
    if request.is_ajax():

        compound_id = request.GET['id']
        metadata = get_single_compound_metadata_online(compound_id)

        if compound_id.upper().startswith('C'): # assume it's kegg

            # TODO: no longer used??!!

            infos = []
            selected = ['FORMULA']
            for key in selected:
                value = metadata[key]
                infos.append({'key': key, 'value': str(value)})

            images = ['http://www.kegg.jp/Fig/compound/' + compound_id + '.gif']
            links = [
                {
                    'text': 'Link to KEGG COMPOUND database',
                    'href': 'http://www.genome.jp/dbget-bin/www_bget?cpd:' + compound_id
                }
            ]

        else: # assume it's ChEBI

            def get_attribute(metadata, attrname):
                try:
                    attr_val = getattr(metadata, attrname)
                except AttributeError:
                    attr_val = ''
                return attr_val

            images = ['http://www.ebi.ac.uk/chebi/displayImage.do?defaultImage=true&imageIndex=0&chebiId=' + compound_id]
            links = [
                {
                    'text': 'Link to ChEBI database',
                    'href': 'https://www.ebi.ac.uk/chebi/searchId.do?chebiId=CHEBI:' + compound_id
                }
            ]

            infos = []
            try:
                for db_link in metadata.DatabaseLinks:
                    if 'KEGG COMPOUND' in str(db_link.type):
                        kegg_id = db_link.data
                        infos.append({'key': 'KEGG ID', 'value': kegg_id})
                        links.append({
                            'text': 'Link to KEGG COMPOUND database',
                            'href': 'http://www.genome.jp/dbget-bin/www_bget?cpd:' + kegg_id
                        })
            except AttributeError:
                pass

            try:
                infos.append({'key': 'FORMULA', 'value': metadata.Formulae[0].data})
            except AttributeError:
                pass
            selected = [
                ('ChEBI ID', 'chebiId'),
                ('Definition', 'definition'),
                ('Monoisotopic Mass', 'monoisotopicMass'),
                ('SMILES', 'smiles'),
                # ('Inchi', 'inchi'),
                # ('InchiKey', 'inchikey'),
            ]
            for key, attribute in selected:
                value = get_attribute(metadata, attribute)
                if value is not None:
                    infos.append({'key': key, 'value': value})


        data = {
            'infos': infos,
            'images': images,
            'links': links
        }
        return JsonResponse(data)


def get_summary_string(reactome_id):
    desc, is_inferred = get_reactome_description(reactome_id, from_parent=False)
    if is_inferred:
        desc, _ = get_reactome_description(reactome_id, from_parent=True)

    summary_list = []
    for s in desc:
        if s['summary_text'] is None:
            continue
        st = s['summary_text'].replace(';', ',')
        summary_list.append(truncate(st))
    summary_str = ';'.join(summary_list)
    return summary_str, is_inferred, desc[0]['species']


def get_reactome_reaction_info(request):
    if request.is_ajax():
        reactome_id = request.GET['id']
        species = urllib.parse.unquote(request.GET['species'])

        infos = []

        # res = get_reactome_content_service(reactome_id)
        # summary_str = res['summation'][0]['text']
        summary_str, is_inferred, inferred_species = get_summary_string(reactome_id)
        infos.append({'key': 'Summary', 'value': summary_str})

        if is_inferred:
            inferred = 'Inferred from %s' % inferred_species
            infos.append({'key': 'Inferred', 'value': inferred})

        # get all the participants
        temp = collections.defaultdict(list)
        results = get_reaction_entities([reactome_id], species)[reactome_id]
        for res in results:
            entity_id = res[1]
            display_name = res[2]
            relationship_types = res[3]
            if len(relationship_types) == 1:  # ignore the sub-complexes
                rel = relationship_types[0]
                temp[rel].append((display_name, entity_id,))

        for k, v in temp.items():
            name_list, url_list = zip(*v) # https://stackoverflow.com/questions/12974474/how-to-unzip-a-list-of-tuples-into-individual-lists
            url_list = map(lambda x: 'https://reactome.org/content/detail/' + x if x is not None else '', url_list)

            name_str = ';'.join(name_list)
            url_str = ';'.join(url_list)
            infos.append({'key': k.title(), 'value': name_str, 'url': url_str})

        images = [
            'https://reactome.org/ContentService/exporter/diagram/' + reactome_id + '.jpg?sel=' + reactome_id + "&quality=7"
        ]
        links = [
            {
                'text': 'Link to Reactome database',
                'href': 'https://reactome.org/content/detail/' + reactome_id
            }
        ]
        data = {
            'infos': infos,
            'images': images,
            'links': links
        }
        return JsonResponse(data)


def get_reactome_pathway_info(request):
    if request.is_ajax():

        pathway_id = request.GET['id']
        species = urllib.parse.unquote(request.GET['species'])
        mapping, id_to_names = pathway_to_reactions([pathway_id], species)
        pathway_reactions = mapping[pathway_id]

        reaction_list = map(lambda x: id_to_names[x], pathway_reactions)
        reaction_str = ';'.join(sorted(reaction_list))

        url_list = map(lambda x: 'https://reactome.org/content/detail/' + x, pathway_reactions)
        url_str = ';'.join(sorted(url_list))

        # res = get_reactome_content_service(pathway_id)
        # summary_str = res['summation'][0]['text']
        summary_str, is_inferred, inferred_species = get_summary_string(pathway_id)

        infos = [{'key': 'Summary', 'value': summary_str}]
        if is_inferred:
            inferred = 'Inferred from %s' % inferred_species
            infos.append({'key': 'Inferred', 'value': inferred})
        infos.append({'key': 'Reactions', 'value': reaction_str, 'url': url_str})

        images = [
            'https://reactome.org/ContentService/exporter/diagram/' + pathway_id + '.jpg?sel=' + pathway_id
        ]
        links = [
            {
                'text': 'Link to Reactome database',
                'href': 'https://reactome.org/content/detail/' + pathway_id
            },
            {
                'text': 'SBML Export',
                'href': 'https://reactome.org/ContentService/exporter/sbml/' + pathway_id + '.xml'
            }
        ]
        data = {
            'infos': infos,
            'images': images,
            'links': links
        }
        return JsonResponse(data)


def truncate(my_str):
    my_str = (my_str[:TRUNCATE_LIMIT] + '...') if len(my_str) > TRUNCATE_LIMIT else my_str
    return my_str
