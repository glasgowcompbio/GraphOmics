from django.db import models
from jsonfield import JSONField
from django.utils import timezone
import collections


from linker.constants import DataType, DataRelationType, InferenceType


class Analysis(models.Model):
    name = models.CharField(max_length=100, null=True)
    description = models.CharField(max_length=1000, null=True)
    timestamp = models.DateTimeField(default=timezone.localtime, null=False)
    metadata = JSONField()

    def get_species_str(self):
        if 'species_list' in self.metadata:
            return ', '.join(self.metadata['species_list'])
        else:
            return ''

    def get_species_list(self):
        if 'species_list' in self.metadata:
            return self.metadata['species_list']
        else:
            return []


class AnalysisData(models.Model):
    analysis = models.ForeignKey(Analysis, on_delete=models.CASCADE)
    json_data = JSONField()
    data_type = models.IntegerField(choices=DataRelationType)


class AnalysisSample(models.Model):
    analysis_data = models.ForeignKey(AnalysisData, on_delete=models.CASCADE)
    sample_name = models.CharField(max_length=100)
    group_name = models.CharField(max_length=100)


class AnalysisResult(models.Model):
    analysis_data = models.ForeignKey(AnalysisData, on_delete=models.CASCADE)
    inference_type = models.IntegerField(choices=InferenceType)
    params = JSONField()
    results = JSONField()
    timestamp = models.DateTimeField(default=timezone.localtime, null=False)