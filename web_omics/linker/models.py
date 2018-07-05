from django.db import models
from jsonfield import JSONField
from django.utils import timezone
from django.conf import settings
import os

from django.contrib.auth import get_user_model

User = get_user_model()

from linker.constants import DataType, DataRelationType, InferenceTypeChoices

class Analysis(models.Model):
    name = models.CharField(max_length=100, null=True)
    description = models.CharField(max_length=1000, null=True)
    timestamp = models.DateTimeField(default=timezone.localtime, null=False)
    metadata = JSONField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)

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


def get_upload_folder(instance, filename):
    upload_folder = "analysis_upload_%s" % instance.pk
    return os.path.abspath(os.path.join(settings.MEDIA_ROOT, upload_folder, filename))


class AnalysisUpload(models.Model):
    analysis = models.OneToOneField(
        Analysis,
        on_delete=models.CASCADE,
        primary_key=True,
    )
    gene_data = models.FileField(blank=True, null=True, upload_to=get_upload_folder)
    gene_design = models.FileField(blank=True, null=True, upload_to=get_upload_folder)
    protein_data = models.FileField(blank=True, null=True, upload_to=get_upload_folder)
    protein_design = models.FileField(blank=True, null=True, upload_to=get_upload_folder)
    compound_data = models.FileField(blank=True, null=True, upload_to=get_upload_folder)
    compound_design = models.FileField(blank=True, null=True, upload_to=get_upload_folder)


class AnalysisData(models.Model):
    analysis = models.ForeignKey(Analysis, on_delete=models.CASCADE)
    json_data = JSONField()
    data_type = models.IntegerField(choices=DataRelationType)


class AnalysisSample(models.Model):
    analysis_data = models.ForeignKey(AnalysisData, on_delete=models.CASCADE)
    sample_name = models.CharField(max_length=100)
    factor = models.CharField(max_length=100, blank=True, null=True)
    level = models.CharField(max_length=100, blank=True, null=True)

class AnalysisResult(models.Model):
    analysis_data = models.ForeignKey(AnalysisData, on_delete=models.CASCADE)
    inference_type = models.IntegerField(choices=InferenceTypeChoices)
    display_name = models.CharField(max_length=1000)
    params = JSONField()
    results = JSONField()
    timestamp = models.DateTimeField(default=timezone.localtime, null=False)


class AnalysisAnnotation(models.Model):
    analysis = models.ForeignKey(Analysis, on_delete=models.CASCADE)
    data_type = models.IntegerField(choices=DataType)
    database_id = models.CharField(max_length=100)
    display_name = models.CharField(max_length=1000)
    annotation = models.CharField(max_length=1000)
    timestamp = models.DateTimeField(default=timezone.localtime, null=False)