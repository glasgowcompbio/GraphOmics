import os

from django import forms
from django_select2.forms import Select2Widget, Select2MultipleWidget

from linker.constants import AddNewDataChoices, InferenceTypeChoices, CompoundDatabaseChoices, \
    MetabolicPathwayOnlyChoices, SELECT_WIDGET_ATTRS, DEFAULT_SPECIES, ShareReadOnlyChoices
from linker.reactome import get_species_dict, get_all_pathways
from linker.models import Analysis, AnalysisUpload

def load_example_data(file_path):
    __location__ = os.path.realpath(
        os.path.join(os.getcwd(), os.path.dirname(__file__)))

    example_file = os.path.join(__location__, file_path)
    with open(example_file, 'r') as myfile:
        example_data = myfile.read()

    return example_data


example_genes = load_example_data('../static/data/uploads/gene_data_example.csv')
example_proteins = ""
example_compounds = load_example_data('../static/data/uploads/compound_data_example.csv')

# example_genes = load_example_data('../static/data/gene_data.csv')
# example_proteins = ""
# example_compounds = load_example_data('../static/data/compound_data.csv')

SPECIES_CHOICES = []
mus_musculus = None
for k, v in get_species_dict().items():
    SPECIES_CHOICES.append((k, v,))
    if v == 'Mus musculus':
        mus_musculus = (k, v,)


default_pathways = get_all_pathways(DEFAULT_SPECIES)
pathway_species_dict = {}
PATHWAY_CHOICES = []
for i, item in enumerate(default_pathways):
    pathway_species, pathway_name, pathway_id = item
    value = '%s (%s)' % (pathway_name, pathway_species)
    PATHWAY_CHOICES.append((pathway_id, value))
    pathway_species_dict[pathway_id] = pathway_species


class CreateAnalysisForm(forms.Form):
    analysis_name = forms.CharField(required=False, widget=forms.TextInput(attrs={'style': 'width: 100%'}))
    analysis_description = forms.CharField(required=False, widget=forms.TextInput(attrs={'style': 'width: 100%'}))
    species = forms.MultipleChoiceField(required=True, choices=SPECIES_CHOICES, initial=mus_musculus[0],
                                        widget=Select2MultipleWidget)
    genes = forms.CharField(required=False,
                            widget=forms.Textarea(attrs={'rows': 6, 'cols': 100, 'style': 'width: 100%'}),
                            initial=example_genes, label='Genes/Transcripts')
    proteins = forms.CharField(required=False,
                               widget=forms.Textarea(attrs={'rows': 6, 'cols': 100, 'style': 'width: 100%'}),
                               initial=example_proteins)
    compounds = forms.CharField(required=False,
                                widget=forms.Textarea(attrs={'rows': 6, 'cols': 100, 'style': 'width: 100%'}),
                                initial=example_compounds)
    metabolic_pathway_only = forms.ChoiceField(required=True, choices=MetabolicPathwayOnlyChoices,
                                widget=Select2Widget,
                                label='Limit to',
                                help_text='<div style="color: gray"><small>Whether to limit the selected pathways to only metabolic pathways.</small></div>')
    compound_database = forms.ChoiceField(required=True, choices=CompoundDatabaseChoices,
                                widget=Select2Widget,
                                label='Query compounds by',
                                help_text='<div style="color: gray"><small>When querying the Reactome knowledge base, '
                                          'compounds will be matched using the identifiers specified above.</small></div>')


class UploadAnalysisForm(forms.ModelForm):
    analysis_name = forms.CharField(required=False, widget=forms.TextInput(attrs={'style': 'width: 100%'}))
    analysis_description = forms.CharField(required=False, widget=forms.TextInput(attrs={'style': 'width: 100%'}))
    species = forms.MultipleChoiceField(required=True, choices=SPECIES_CHOICES, widget=Select2MultipleWidget)
    metabolic_pathway_only = forms.ChoiceField(required=True, choices=MetabolicPathwayOnlyChoices,
                                widget=Select2Widget,
                                label='Limit to',
                                help_text='<div style="color: gray"><small>Whether to limit the selected pathways to only metabolic pathways.</small></div>')
    compound_database = forms.ChoiceField(required=True, choices=CompoundDatabaseChoices,
                                widget=Select2Widget,
                                label='Query compounds by',
                                help_text='<div style="color: gray"><small>When querying the Reactome knowledge base, '
                                          'compounds will be matched using the identifiers specified above.</small></div>')
    class Meta:
        model = AnalysisUpload
        fields = ('analysis_name', 'analysis_description', 'species',
                  'gene_data', 'gene_design',
                  'protein_data', 'protein_design',
                  'compound_data', 'compound_design')


class BaseInferenceForm(forms.Form):
    data_type = forms.ChoiceField(required=True, choices=AddNewDataChoices, widget=Select2Widget(attrs=SELECT_WIDGET_ATTRS))
    inference_type = forms.ChoiceField(required=True, choices=InferenceTypeChoices, widget=Select2Widget(attrs=SELECT_WIDGET_ATTRS))


class ShareAnalysisForm(forms.Form):
    username = forms.CharField(required=True, widget=forms.TextInput(attrs={'size': 100}))
    share_type = forms.ChoiceField(required=True, choices=ShareReadOnlyChoices, widget=Select2Widget(attrs=SELECT_WIDGET_ATTRS))