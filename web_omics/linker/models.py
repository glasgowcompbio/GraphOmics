from django.db import models
from jsonfield import JSONField
from django.utils import timezone
import collections


from linker.constants import DataType, DataRelationType, InferenceType


class Analysis(models.Model):
    name = models.CharField(max_length=100, null=True)
    description = models.CharField(max_length=1000, null=True)
    timestamp = models.DateTimeField(default=timezone.localtime, null=False)
    metadata = JSONField(load_kwargs={'object_pairs_hook': collections.OrderedDict})

    def get_species(self):
        if 'species_list' in self.metadata:
            return ','.join(self.metadata['species_list'])
        else:
            return ''

class AnalysisData(models.Model):
    analysis = models.ForeignKey(Analysis, on_delete=models.CASCADE)
    json_data = JSONField(load_kwargs={'object_pairs_hook': collections.OrderedDict})
    data_type = models.IntegerField(choices=DataRelationType)


class AnalysisSample(models.Model):
    analysis_data = models.ForeignKey(AnalysisData, on_delete=models.CASCADE)
    sample_name = models.CharField(max_length=100)
    group_name = models.CharField(max_length=100)


class AnalysisResult(models.Model):
    analysis_data = models.ForeignKey(AnalysisData, on_delete=models.CASCADE)
    inference_type = models.IntegerField(choices=InferenceType)
    params = JSONField(load_kwargs={'object_pairs_hook': collections.OrderedDict})
    results = JSONField(load_kwargs={'object_pairs_hook': collections.OrderedDict})
    timestamp = models.DateTimeField(default=timezone.localtime, null=False)