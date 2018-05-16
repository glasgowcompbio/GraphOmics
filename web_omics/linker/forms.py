# forms.py for decomposition
from django import forms
import os
from linker.reactome import get_species_list

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
# example_compounds = load_example_data('../static/data/compound_ids.csv')

species_list = get_species_list()
SPECIES_CHOICES = []
mus_musculus = None
for idx, s in enumerate(species_list):
    SPECIES_CHOICES.append((idx, s, ))
    if s == 'Mus musculus':
        mus_musculus = (idx, s, )

class LinkerForm(forms.Form):
    genes = forms.CharField(required = False,
                               widget = forms.Textarea(attrs={'rows': 10, 'cols': 120}),
                               initial = example_genes)
    proteins = forms.CharField(required = False,
                               widget = forms.Textarea(attrs={'rows': 10, 'cols': 120}),
                               initial = example_proteins)
    compounds = forms.CharField(required = False,
                               widget = forms.Textarea(attrs={'rows': 10, 'cols': 120}),
                               initial = example_compounds)

    def __init__(self, *args, **kwargs):
        super(LinkerForm, self).__init__(*args, **kwargs)
        self.fields['species'] = forms.ChoiceField(required = True,
                                                   choices = SPECIES_CHOICES,
                                                   initial = mus_musculus[0])