from django.shortcuts import render
from django.views.generic.edit import FormView

from linker.forms import LinkerForm
from linker.reactome import get_species_dict
from linker.views.functions import reactome_mapping, save_analysis


class CreateAnalysisView(FormView):
    template_name = 'linker/create_analysis.html'
    form_class = LinkerForm
    success_url = 'linker/explore_data.html'

    def form_valid(self, form):
        analysis_name = form.cleaned_data['analysis_name']
        analysis_desc = form.cleaned_data['analysis_description']
        genes_str = form.cleaned_data['genes']
        proteins_str = form.cleaned_data['proteins']
        compounds_str = form.cleaned_data['compounds']
        species_dict = get_species_dict()
        species_list = [species_dict[x] for x in form.cleaned_data['species']]

        results = reactome_mapping(self.request, genes_str, proteins_str, compounds_str, species_list)
        analysis, data = save_analysis(analysis_name, analysis_desc,
                                       genes_str, proteins_str, compounds_str,
                                       results, species_list)
        context = {
            'data': data,
            'analysis_id': analysis.pk,
            'analysis_name': analysis.name,
            'analysis_description': analysis.description,
            'analysis_species': analysis.get_species_str()
        }
        return render(self.request, self.success_url, context)