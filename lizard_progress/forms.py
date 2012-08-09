from django import forms
from django.conf import settings
from django.contrib.auth.decorators import permission_required
from django.db import transaction
from django.template.defaultfilters import slugify
from django.utils.decorators import method_decorator
from django.views.generic.edit import CreateView
from django.views.generic.edit import UpdateView
from django.views.generic.edit import DeleteView
from models import Project, Contractor
import os

### Form Wizard experiments
### Directly available in Django 1.4!
### Steps are defined in urls.py

from django.shortcuts import render_to_response
from django.contrib.auth.models import User
from django.contrib.formtools.wizard.views import SessionWizardView
from django.core.files.storage import FileSystemStorage


def handle_uploaded_file(f):
    with open('/tmp/uploaded_file.pdf', 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)


class ProjectWizard(SessionWizardView):

    #file_storage = settings.DEFAULT_FILE_STORAGE
    #file_storage = FileSystemStorage(location="/tmp/hdsr")
    file_storage = FileSystemStorage()

    def get_form_initial(self, step):
        """Returns a dictionary with initial form data for the current step."""
        form_initial = super(ProjectWizard, self).get_form_initial(step)
        if step == "0":
            form_initial['superuser'] = self.request.user
        return form_initial

    def get_template_names(self):
        #return ("lizard_progress/wizard_form.html", "lizard_progress/wizard_form.html", "lizard_progress/wizard_form.html")
        return "lizard_progress/wizard_form.html"

    def done(self, form_list, **kwargs):
        # Save the new project.
        project = form_list[0].save(commit=False)
        project.slug = slugify(project.name)
        project.save()
        return render_to_response('lizard_progress/done.html', {
            'form_data': [form.cleaned_data for form in form_list],
        })


class ProjectForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(ProjectForm, self).__init__(*args, **kwargs)
        print dir(self)
        print args
        print kwargs

    def clean_name(self):
        """Validates and returns the name of a new project."""
        # Since the `slug` field is excluded, it will not
        # be checked automatically for uniqueness.
        name = self.cleaned_data['name']
        if Project.objects.filter(slug=slugify(name)).exists():
            msg = "Kies a.u.b. een andere Projectnaam."
            raise forms.ValidationError(msg)
        return name

    class Meta:
        model = Project
        exclude = ('slug',)



MEASUREMENT_TYPES_CHOICES = (
    ('dwarsprofiel', 'Dwarsprofiel'),
    ('oeverfoto', 'Oeverfoto'),
    ('oeverkenmerk', 'Oeverkenmerk'),
    ('foto', 'Foto'),
    ('meting', 'Meting')
)


class MeasurementTypeForm(forms.Form):
    measurement_types = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        choices=MEASUREMENT_TYPES_CHOICES,
        label="Uit te voeren metingen")


class LocationForm(forms.Form):
    dbf = forms.FileField()
    prj = forms.FileField(required=False)
    shp = forms.FileField()
    shx = forms.FileField()

    def clean_dbf(self):
        dbf = self.cleaned_data['dbf']
        self.check_ext(dbf.name, '.dbf')

    def clean_shp(self):
        shp = self.cleaned_data['shp']
        self.check_ext(shp.name, '.shp')

    def check_ext(self, filename, ext):
        if not os.path.splitext(filename)[1].lower() == ext:
            msg = "Dit is geen %s bestand." % (ext,)
            raise forms.ValidationError(msg)

### Contractor


class ContractorWizard(SessionWizardView):

    @method_decorator(permission_required('lizard_progress.add_project'))
    def dispatch(self, *args, **kwargs):
        return super(ContractorWizard, self).dispatch(*args, **kwargs)

    def get_template_names(self):
        return "lizard_progress/wizard_form.html"

    @transaction.commit_on_success
    def done(self, form_list, **kwargs):
        if form_list[0].cleaned_data['user_choice_field'] == '1':
            user = form_list[1].cleaned_data['user']
        else:
            user = form_list[1].save(commit=False)
            user.set_password(user.password)
            user.save()
        contractor = form_list[0].save(commit=False)
        contractor.slug = slugify(contractor.name)
        contractor.user = user
        contractor.save()

        return render_to_response('lizard_progress/done.html', {
            'form_data': [form.cleaned_data for form in form_list],
        })


USER_CHOICES = (
    ('1', 'Een bestaand account hergebruiken'),
    ('2', 'Een nieuw account aanmaken'),
)


class ContractorForm(forms.ModelForm):
    name = forms.CharField(label='Uitvoerder:', max_length=50) 
    user_choice_field = forms.ChoiceField(
        label='Loginnaam en wachtwoord',
        widget=forms.RadioSelect,
        choices=USER_CHOICES
    )

    # TODO: (`project`, `slug`) should be unique

    class Meta:
        model = Contractor
        exclude = ('slug', 'user',)


def existing_user_condition(wizard):
    """Returns False if the ExistingUserForm step should be skipped."""
    cleaned_data = wizard.get_cleaned_data_for_step('0') or {}
    return cleaned_data.get('user_choice_field', '1') == '1'


class ExistingUserForm(forms.Form):
    user = forms.ModelChoiceField(
        label = 'Loginnaam',
        queryset=User.objects.all()
    )


def new_user_condition(wizard):
    """Returns False if the NewUserForm step should be skipped."""
    cleaned_data = wizard.get_cleaned_data_for_step('0') or {}
    return cleaned_data.get('user_choice_field', '2') == '2'


class NewUserForm(forms.ModelForm):
    password = forms.CharField(
        label="Wachtwoord",
        widget=forms.PasswordInput(attrs={'autocomplete':'off'}),
        max_length = 128
    )
    password_again = forms.CharField(
        label="Bevestiging wachtwoord",
        widget=forms.PasswordInput(attrs={'autocomplete':'off'}),
        max_length = 128,
        help_text='Vul hetzelfde wachtwoord als hierboven in, ter bevestiging.'
    )

    # TODO: `password` should match `password_again`

    class Meta:
        model = User
        fields = ('username', 'password')


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

