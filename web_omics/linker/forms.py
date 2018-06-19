# forms.py for decomposition
from django import forms
from django_select2.forms import Select2MultipleWidget
import os
from linker.reactome import get_species_dict

def load_example_data(file_path):

    __location__ = os.path.realpath(
        os.path.join(os.getcwd(), os.path.dirname(__file__)))

    example_file = os.path.join(__location__, file_path)
    with open(example_file, 'r') as myfile:
        example_data = myfile.read()

    return example_data

example_genes = load_example_data('../static/data/gene_data_small.csv')
example_proteins = ""
example_compounds = load_example_data('../static/data/compound_data.csv')

# example_genes = load_example_data('../static/data/gene_data.csv')
# example_proteins = ""
# example_compounds = load_example_data('../static/data/compound_data.csv')

SPECIES_CHOICES = []
mus_musculus = None
for k, v in get_species_dict().items():
    SPECIES_CHOICES.append((k, v, ))
    if v == 'Mus musculus':
        mus_musculus = (k, v, )

class LinkerForm(forms.Form):

    analysis_name = forms.CharField(required = True, widget=forms.TextInput(attrs={'size':100}))
    analysis_description = forms.CharField(required = False,
                               widget = forms.Textarea(attrs={'rows': 3, 'cols': 100}))
    species = forms.MultipleChoiceField(required=True, choices=SPECIES_CHOICES, initial=mus_musculus[0],
                                        widget=Select2MultipleWidget)
    genes = forms.CharField(required = False,
                               widget = forms.Textarea(attrs={'rows': 6, 'cols': 100}),
                               initial = example_genes, label='Genes/Transcripts')
    proteins = forms.CharField(required = False,
                               widget = forms.Textarea(attrs={'rows': 6, 'cols': 100}),
                               initial = example_proteins)
    compounds = forms.CharField(required = False,
                               widget = forms.Textarea(attrs={'rows': 6, 'cols': 100}),
                               initial = example_compounds)