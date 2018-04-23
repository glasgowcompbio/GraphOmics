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

example_transcripts = load_example_data('ens_id.txt')
example_genes = ""
example_proteins = ""
example_compounds = load_example_data('kegg_id.txt')

species_list = get_species_list()
SPECIES_CHOICES = []
for idx, s in enumerate(species_list):
    SPECIES_CHOICES.append((idx, s, ))

class LinkerForm(forms.Form):
    # genes = forms.CharField(required = False,
    #                            widget = forms.Textarea(attrs={'rows': 4, 'cols': 40}),
    #                            initial = example_genes)
    transcripts = forms.CharField(required = False,
                               widget = forms.Textarea(attrs={'rows': 4, 'cols': 40}),
                               initial = example_transcripts)
    proteins = forms.CharField(required = False,
                               widget = forms.Textarea(attrs={'rows': 4, 'cols': 40}),
                               initial = example_proteins)
    compounds = forms.CharField(required = False,
                               widget = forms.Textarea(attrs={'rows': 4, 'cols': 40}),
                               initial = example_compounds)

    def __init__(self, *args, **kwargs):
        super(LinkerForm, self).__init__(*args, **kwargs)
        self.fields['species'] = forms.ChoiceField(required = True,
                                                   choices = SPECIES_CHOICES)