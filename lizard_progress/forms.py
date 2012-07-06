from django import forms
from django.template.defaultfilters import slugify
from django.views.generic.edit import CreateView
from django.views.generic.edit import UpdateView
from django.views.generic.edit import DeleteView
from models import Project, Contractor


### Form Wizard experiments
### Directly available in Django 1.4!
### Steps are defined in urls.py

from django.shortcuts import render_to_response
from django.contrib.formtools.wizard.views import SessionWizardView


class ProjectWizard(SessionWizardView):

    def get_template_names(self):
        return ("lizard_progress/wizard_form.html", "lizard_progress/wizard_form.html")

    def done(self, form_list, **kwargs):
        return render_to_response('lizard_progress/done.html', {
            'form_data': [form.cleaned_data for form in form_list],
        })


class ProjectForm(forms.ModelForm):
    name = forms.CharField(label='Projectnaam', max_length=50)
    class Meta:
        model = Project
        exclude = ('slug',)


class ContractorForm(forms.ModelForm):
    name = forms.CharField(label='Contractor')
    class Meta:
        model = Contractor


### Form handling with class-based views experiments

class ProjectCreate(CreateView):
    form_class = ProjectForm
    template_name = "lizard_progress/project.html"
    success_url = '/'
    model = Project

    def form_valid(self, form):
        form.instance.slug = slugify(form.cleaned_data['name'])
        return super(ProjectCreate, self).form_valid(form)


class ProjectUpdate(UpdateView):
    template_name = "lizard_progress/project.html"
    model = Project


class ProjectDelete(DeleteView):
    template_name = "lizard_progress/project.html"
    model = Project

