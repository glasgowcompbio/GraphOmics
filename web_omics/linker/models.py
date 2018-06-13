from django.db import models
from jsonfield import JSONField
import collections
import datetime


class Analysis(models.Model):

    name = models.CharField(max_length=100, null=True)
    species = models.CharField(max_length=100, null=True)
    description = models.CharField(max_length=1000, null=True)
    timestamp = models.DateField(default= datetime.date.today, null=False)

    genes_json = JSONField(load_kwargs={'object_pairs_hook': collections.OrderedDict})
    proteins_json = JSONField(load_kwargs={'object_pairs_hook': collections.OrderedDict})
    compounds_json = JSONField(load_kwargs={'object_pairs_hook': collections.OrderedDict})
    reactions_json = JSONField(load_kwargs={'object_pairs_hook': collections.OrderedDict})
    pathways_json = JSONField(load_kwargs={'object_pairs_hook': collections.OrderedDict})
    gene_proteins_json = JSONField(load_kwargs={'object_pairs_hook': collections.OrderedDict})
    protein_reactions_json = JSONField(load_kwargs={'object_pairs_hook': collections.OrderedDict})
    compound_reactions_json = JSONField(load_kwargs={'object_pairs_hook': collections.OrderedDict})
    reaction_pathways_json = JSONField(load_kwargs={'object_pairs_hook': collections.OrderedDict})