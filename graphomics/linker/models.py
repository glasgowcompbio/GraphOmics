import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone
from jsonfield import JSONField
from django.core.files import File

User = get_user_model()

from linker.constants import DataType, DataRelationType, InferenceTypeChoices

class Analysis(models.Model):
    name = models.CharField(max_length=100, null=True)
    description = models.CharField(max_length=1000, null=True)
    publication = models.CharField(max_length=1000, null=True)
    publication_link = models.CharField(max_length=1000, null=True)
    timestamp = models.DateTimeField(default=timezone.localtime, null=False)
    public = models.BooleanField(default=False)
    metadata = JSONField()
    users = models.ManyToManyField(User, through='Share')

    class Meta:
        verbose_name_plural = "Analyses"

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

    def get_owner(self):
        for share in self.share_set.all():
            if share.owner:
                return share.user

    def get_read_only_status(self, user):
        for share in self.share_set.all(): # search shares for this user
            if share.user == user:
                if share.owner: # owner can always edit
                    return False
                return share.read_only # otherwise check the read-only field
        return False

    def get_read_only_str(self, user):
        read_only = self.get_read_only_status(user)
        msg = 'Read Only' if read_only else 'Edit'
        return msg

    def get_shared(self, user):
        for share in self.share_set.all(): # search shares for this user
            if share.user == user:
                return True
        return False

    def has_mofa_data(self):
        file = self.analysisupload.mofa_data
        if file and file.storage.exists(file.name):
            return file and file.storage.exists(file.name)
        else:
            return False

    def has_gene_data(self):
        file = self.analysisupload.gene_data
        if file and file.storage.exists(file.name):
            return file and file.storage.exists(file.name)
        else:
            return False

    def has_protein_data(self):
        file = self.analysisupload.protein_data
        if file and file.storage.exists(file.name):
            return file and file.storage.exists(file.name)
        else:
            return False

    def has_compound_data(self):
        file = self.analysisupload.compound_data
        if file and file.storage.exists(file.name):
            return file and file.storage.exists(file.name)
        else:
            return False

    def has_metadata(self):
        file = self.analysisupload.metadata
        if file and file.storage.exists(file.name):
            return file and file.storage.exists(file.name)
        else:
            return False

    def get_mofa_hdf5_path(self):
        if self.has_mofa_data():
            return self.analysisupload.mofa_data.path
        else:
            return None


    def get_gene_data_path(self):
        if self.has_gene_data():
            return self.analysisupload.gene_data.path
        else:
            return None

    def get_protein_data_path(self):
        if self.has_protein_data():
            return self.analysisupload.protein_data.path
        else:
            return None

    def get_compound_data_path(self):
        if self.has_compound_data():
            return self.analysisupload.compound_data.path
        else:
            return None

    def get_gene_design_path(self):
        if self.has_gene_data():
            return self.analysisupload.gene_design.path
        else:
            return None

    def get_protein_design_path(self):
        if self.has_protein_data():
            return self.analysisupload.protein_design.path
        else:
            return None

    def get_compound_design_path(self):
        if self.has_compound_data():
            return self.analysisupload.compound_design.path
        else:
            return None

    def get_metadata_path(self):
        if self.has_metadata():
            return self.analysisupload.metadata.path
        else:
            return None

    def set_mofa_hdf5_path(self, filePath):
        with open(filePath, 'rb') as f:
            fileName = self.name + '_mofa_data.hdf5'
            self.analysisupload.mofa_data.save(fileName, File(f))
            os.remove(filePath)

    def __str__(self):
        return self.name


class Share(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    analysis = models.ForeignKey(Analysis, on_delete=models.CASCADE)
    read_only = models.BooleanField()
    owner = models.BooleanField()

    def __str__(self):
        return 'User=%s, Analysis=%s, read_only=%s, owner=%s' % (self.user, self.analysis, self.read_only, self.owner)

    def get_read_only_str(self):
        msg = 'Read Only' if self.read_only else 'Edit'
        return msg


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
    mofa_data = models.FileField(blank=True, null=True, upload_to=get_upload_folder)
    metadata = models.FileField(blank=True, null=True, upload_to=get_upload_folder)


class AnalysisData(models.Model):
    analysis = models.ForeignKey(Analysis, on_delete=models.CASCADE)
    data_type = models.IntegerField(choices=DataRelationType)
    json_data = JSONField()
    json_design = JSONField()
    metadata = JSONField(blank=True, null=True)
    timestamp = models.DateTimeField(default=timezone.localtime, null=False)

    class Meta:
        verbose_name_plural = "Analysis Data"

    def get_data_type_str(self):
        try:
            return dict(DataRelationType)[self.data_type]
        except KeyError:
            return ''

    def __str__(self):
        return '%s data for analysis %d' % (self.get_data_type_str(), self.analysis.pk)


class AnalysisHistory(models.Model):
    analysis = models.ForeignKey(Analysis, on_delete=models.CASCADE)
    display_name = models.CharField(max_length=1000, blank=True, null=True)
    analysis_data = models.ForeignKey(AnalysisData, on_delete=models.CASCADE)
    inference_type = models.IntegerField(choices=InferenceTypeChoices, blank=True, null=True)
    inference_data = JSONField()
    timestamp = models.DateTimeField(default=timezone.localtime, null=False)

    class Meta:
        verbose_name_plural = "Analysis Histories"

    def get_data_type_str(self):
        return self.analysis_data.get_data_type_str()

    def get_inference_type_str(self):
        try:
            return dict(InferenceTypeChoices)[self.inference_type]
        except KeyError:
            return ''


    def __str__(self):
        return '%s (%s) timestamp=%s' % (self.display_name, self.analysis_data, self.timestamp.strftime("%Y-%m-%d %H:%M:%S"))


class AnalysisAnnotation(models.Model):
    analysis = models.ForeignKey(Analysis, on_delete=models.CASCADE)
    data_type = models.IntegerField(choices=DataType)
    database_id = models.CharField(max_length=100)
    display_name = models.CharField(max_length=1000)
    annotation = models.CharField(max_length=1000)
    timestamp = models.DateTimeField(default=timezone.localtime, null=False)

    class Meta:
        verbose_name_plural = "Analysis Annotations"

    def __str__(self):
        return '%s data_type=%d %s' % (self.analysis.name, self.data_type, self.display_name)


class AnalysisGroup(models.Model):
    analysis = models.ForeignKey(Analysis, on_delete=models.CASCADE)
    linker_state = JSONField()
    display_name = models.CharField(max_length=1000)
    description = models.CharField(max_length=1000)
    timestamp = models.DateTimeField(default=timezone.localtime, null=False)

    class Meta:
        verbose_name_plural = "Analysis Groups"

    def __str__(self):
        return '%s data_type=%d %s' % (self.analysis.name, self.data_type, self.display_name)
