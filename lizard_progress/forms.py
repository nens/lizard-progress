"""Forms, mainly used as steps by form wizards."""

from django import forms
from django.contrib.auth.models import User
from django.template.defaultfilters import slugify
from django.views.generic.edit import CreateView
from django.views.generic.edit import DeleteView
from django.views.generic.edit import UpdateView
from lizard_progress.models import (AvailableMeasurementType, Contractor,
    Project)
import os


class ProjectForm(forms.ModelForm):

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

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(ContractorForm, self).__init__(*args, **kwargs)
        self.fields['project'].queryset = \
            Project.objects.filter(superuser=user)

    class Meta:
        model = Contractor
        exclude = ('slug', 'user',)


def existing_user_condition(wizard):
    """Returns False if the ExistingUserForm step should be skipped."""
    cleaned_data = wizard.get_cleaned_data_for_step('0') or {}
    return cleaned_data.get('user_choice_field', '1') == '1'


class ExistingUserForm(forms.Form):
    user = forms.ModelChoiceField(
        label='Loginnaam',
        queryset=User.objects.all()
    )


def new_user_condition(wizard):
    """Returns False if the NewUserForm step should be skipped."""
    cleaned_data = wizard.get_cleaned_data_for_step('0') or {}
    return cleaned_data.get('user_choice_field', '2') == '2'


class NewUserForm(forms.ModelForm):
    password = forms.CharField(
        label="Wachtwoord",
        widget=forms.PasswordInput(attrs={'autocomplete': 'off'}),
        max_length=128
    )
    password_again = forms.CharField(
        label="Bevestiging wachtwoord",
        widget=forms.PasswordInput(attrs={'autocomplete': 'off'}),
        max_length=128,
        help_text='Vul hetzelfde wachtwoord als hierboven in, ter bevestiging.'
    )

    def clean(self):
        cleaned_data = super(NewUserForm, self).clean()
        password = cleaned_data.get("password")
        password_again = cleaned_data.get("password_again")

        if password != password_again:
            msg = "U moet twee keer hetzelfde wachtwoord invoeren."
            raise forms.ValidationError(msg)

        return cleaned_data

    class Meta:
        model = User
        fields = ('username', 'password')


class ProjectChoiceForm(forms.Form):
    """Form that allows the selection of a single `Project`.

    The currently logged-in user can only choose from
    projects he owns (i.e. is superuser of).
    """

    project = forms.ModelChoiceField(queryset=None)

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(ProjectChoiceForm, self).__init__(*args, **kwargs)
        self.fields['project'].queryset = \
            Project.objects.filter(superuser=user)


class ContractorChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, contractor):
        return contractor.name


class ContractorChoiceForm(forms.Form):
    """Form that allows the selection of a single `Contractor`.

    The currently logged-in user can only choose from
    contractors associated with the `Project` that
    was selected in a previous step.
    """

    contractor = ContractorChoiceField(queryset=None, label='Uitvoerder')

    def __init__(self, *args, **kwargs):
        project = kwargs.pop('project', None)
        super(ContractorChoiceForm, self).__init__(*args, **kwargs)
        self.fields['contractor'].queryset = \
            Contractor.objects.filter(project=project)


class MeasurementTypeForm(forms.Form):
    """Displays `AvailableMeasurementTypes` to choose from."""

    measurement_types = forms.ModelMultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        queryset=AvailableMeasurementType.objects.all(),
        label="Uit te voeren werkzaamheden"
    )


class ExtFileField(forms.FileField):
    """A `FileField` that validates the filename extension.

    The extensions allowed are passed as a list to the
    constructor, e.g.: ExtFileField(exts=[".dbf"])
    """

    def __init__(self, *args, **kwargs):
        self.exts = [ext.lower() for ext in kwargs.pop("exts")]
        super(ExtFileField, self).__init__(*args, **kwargs)

    def validate(self, value):
        super(ExtFileField, self).validate(value)
        if value:
            ext = os.path.splitext(value.name)[1]
            if ext.lower() not in self.exts:
                msg = "Verkeerd bestandsformaat."
                raise forms.ValidationError(msg)


class ShapefileForm(forms.Form):
    """Form for uploading a shapefile."""

    dbf = ExtFileField(exts=[".dbf"])
    prj = ExtFileField(exts=[".prj"], required=False, help_text="(Optioneel)")
    shp = ExtFileField(exts=[".shp"])
    shx = ExtFileField(exts=[".shx"])

    def clean(self):
        cleaned_data = super(ShapefileForm, self).clean()

        if self.errors:
            return cleaned_data

        # Since there are no errors, `cleaned_data` has all required fields.

        dbf = os.path.splitext(cleaned_data.get("dbf").name)[0]
        shp = os.path.splitext(cleaned_data.get("shp").name)[0]
        shx = os.path.splitext(cleaned_data.get("shx").name)[0]

        # According to http://en.wikipedia.org/wiki/Shapefile,
        # a `.prj` file is not mandatory, but if it is not
        # absent, it has to have the same filename.

        prj = cleaned_data.get("prj", None)
        if prj:
            prj = os.path.splitext(prj.name)[0]
        else:
            prj = dbf

        if dbf == prj == shp == shx:
            pass
        else:
            msg = ("De geselecteerde bestanden horen "
                + "niet tot dezelfde shapefile.")
            raise forms.ValidationError(msg)

        return cleaned_data


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
    model = Project
