from django import forms
from django.conf import settings
from django.contrib.auth.decorators import permission_required
from django.db import transaction
from django.template.defaultfilters import slugify
from django.utils.decorators import method_decorator
from django.views.generic.edit import CreateView
from django.views.generic.edit import UpdateView
from django.views.generic.edit import DeleteView
from models import (Area, Contractor, Location, MeasurementType, Project,
    ScheduledMeasurement)
import os
import osgeo.ogr

### Form Wizard experiments
### Directly available in Django 1.4!
### Steps are defined in urls.py

from django.shortcuts import render_to_response
from django.contrib.auth.models import User
from django.contrib.formtools.wizard.views import SessionWizardView
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponseRedirect

from django.contrib import messages
from django.contrib.gis.geos import fromstr, Point


MEASUREMENT_TYPES = {
    '1': {'name': 'Dwarsprofiel', 'icon_missing': 'bullets/squarered16.png',   'icon_complete': 'bullets/squaregreen16.png',   'choice': 'Dwarsprofiel'},
    '2': {'name': 'Oeverfoto',    'icon_missing': 'camera_missing.png',        'icon_complete': 'camera_present.png',          'choice': 'Oeverfoto'},
    '3': {'name': 'Oeverkenmerk', 'icon_missing': 'bullets/trianglered16.png', 'icon_complete': 'bullets/trianglegreen16.png', 'choice': 'Oeverkenmerk'},
    '4': {'name': 'Foto',         'icon_missing': 'camera_missing.png',        'icon_complete': 'camera_present.png',          'choice': 'Foto'},
    '5': {'name': 'Meting',       'icon_missing': 'bullets/squarered16.png',   'icon_complete': 'bullets/squaregreen16.png',   'choice': 'Meting'},
}


def handle_uploaded_file(f):
    with open('/tmp/uploaded_file.pdf', 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)


class ProjectWizard(SessionWizardView):
    """Form wizard for creating a new `Project`.

    Usage of this wizard requires `lizard_progress.add_project` permission.
    """

    @method_decorator(permission_required('lizard_progress.add_project'))
    def dispatch(self, *args, **kwargs):
        return super(ProjectWizard, self).dispatch(*args, **kwargs)

    def get_form_initial(self, step):
        """Returns a dictionary with initial form data for the current step."""
        form_initial = super(ProjectWizard, self).get_form_initial(step)
        if step == "0":
            form_initial['superuser'] = self.request.user
        return form_initial

    def get_template_names(self):
        return ["lizard_progress/new_project.html"]

    @transaction.commit_on_success
    def done(self, form_list, **kwargs):
        # Save the new project.
        project = form_list[0].save(commit=False)
        project.slug = slugify(project.name)
        project.save()
        if False:
            # For development purposes.
            return render_to_response('lizard_progress/done.html', {
                'form_data': [form.cleaned_data for form in form_list],
            })
        else:
            msg = 'Het aanmaken van project "%s" was succesvol.' % project.name
            messages.info(self.request, msg)
            return HttpResponseRedirect('/progress/admin/')


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


### Contractor


class ContractorWizard(SessionWizardView):
    """Form wizard for creating a new `Contractor`.

    Usage of this wizard requires `lizard_progress.add_project` permission.
    """

    @method_decorator(permission_required('lizard_progress.add_project'))
    def dispatch(self, *args, **kwargs):
        return super(ContractorWizard, self).dispatch(*args, **kwargs)

    def get_form_kwargs(self, step):
        form_kwargs = super(ContractorWizard, self).get_form_kwargs(step)
        if step == '0':
            form_kwargs['user'] = self.request.user
        return form_kwargs

    def get_template_names(self):
        return ["lizard_progress/new_contractor.html"]

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
        if False:
            # For development purposes.
            return render_to_response('lizard_progress/done.html', {
                'form_data': [form.cleaned_data for form in form_list],
            })
        else:
            msg = ('Het toekennen van uitvoerder "%s" aan project "%s" was ' +
                'succesvol.') % (contractor.name, contractor.project.name)
            messages.info(self.request, msg)
            return HttpResponseRedirect('/progress/admin/')


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


### Activities


class ActivitiesWizard(SessionWizardView):
    """Form wizard for creating a new `Contractor`.

    Usage of this wizard requires `lizard_progress.add_project` permission.
    """

    #file_storage = settings.DEFAULT_FILE_STORAGE
    #file_storage = FileSystemStorage(location="/tmp/hdsr")
    file_storage = FileSystemStorage()

    @method_decorator(permission_required('lizard_progress.add_project'))
    def dispatch(self, *args, **kwargs):
        return super(ActivitiesWizard, self).dispatch(*args, **kwargs)

    def get_form_kwargs(self, step):
        form_kwargs = super(ActivitiesWizard, self).get_form_kwargs(step)
        if step == '0':
            form_kwargs['user'] = self.request.user
        elif step == '1':
            form_kwargs['project'] = \
                self.get_cleaned_data_for_step('0')['project']
        return form_kwargs

    def get_template_names(self):
        if self.steps.current == '3':
            return ["lizard_progress/new_activities_step3.html"]
        return ["lizard_progress/new_activities.html"]

    @transaction.commit_on_success
    def done(self, form_list, **kwargs):
        self.__process_shapefile(form_list)
        self.__save_measurement_types(form_list)
        self.__save_area(form_list)
        self.__save_locations(form_list)
        self.__save_scheduled_measurements(form_list)
        if False:
            # For development purposes.
            return render_to_response('lizard_progress/done.html', {
                'form_data': [form.cleaned_data for form in form_list],
            })
        else:
            contractor = form_list[1].cleaned_data['contractor']
            msg = ('Het toewijzen van werkzaamheden aan uitvoerder '
                + '"%s" binnen project "%s" was succesvol.') % (
                contractor.name, contractor.project.name)
            messages.info(self.request, msg)
            return HttpResponseRedirect('/progress/admin/')

    def __process_shapefile(self, form_list):
        unique_ids = []
        shp = form_list[3].cleaned_data['shp']
        shapefile = osgeo.ogr.Open(str(shp.file.name))
        layer = shapefile.GetLayer(0)
        for featureNum in range(layer.GetFeatureCount()):
            feature = layer.GetFeature(featureNum)
            unique_id = feature.GetField("ID_DWP")
            unique_ids.append(unique_id)
        self.unique_ids = set(unique_ids)

    # TODO: the object model requires a major overhaul. Currently,
    # a `MeasurementType` cannot exist without a `Project`.
    # A many-to-many relationship seems more appropriate.
    def __save_measurement_types(self, form_list):
        project = form_list[0].cleaned_data['project']
        for key in form_list[2].cleaned_data['measurement_types']:
            if not MeasurementType.objects.filter(project=project,
                name=MEASUREMENT_TYPES[key]['name']).exists():
                MeasurementType(
                    project=project,
                    name=MEASUREMENT_TYPES[key]['name'],
                    slug = slugify(MEASUREMENT_TYPES[key]['name']),
                    icon_missing = MEASUREMENT_TYPES[key]['icon_missing'],
                    icon_complete = MEASUREMENT_TYPES[key]['icon_complete']
                ).save()

    # Within a project, locations can be assigned to different
    # areas, for example `North`, `East`, `South`, and `West`.
    # This information cannot be automatically deduced from
    # the shape files yet. For that reason, we'll assign
    # all locations to a single `Area`.
    def __save_area(self, form_list):
        project = form_list[0].cleaned_data['project']
        self.area, _ = Area.objects.get_or_create(project=project,
            name=project.name, slug=project.slug)

    # TODO: the object model requires a major overhaul. Currently,
    # a specific `Location` can only be part of one `Project`.
    # A many-to-many relationship seems more appropriate.
    def __save_locations(self, form_list):
        project = form_list[0].cleaned_data['project']
        unique_ids = set(Location.objects.filter(
            project=project).values_list('unique_id', flat=True))
        locations = []
        contractor = form_list[1].cleaned_data['contractor']
        shp = form_list[3].cleaned_data['shp']
        shapefile = osgeo.ogr.Open(str(shp.file.name))
        for layerNum in range(shapefile.GetLayerCount()):
            layer = shapefile.GetLayer(layerNum)
            for featureNum in range(layer.GetFeatureCount()):
                feature = layer.GetFeature(featureNum)
                unique_id = feature.GetField("ID_DWP")
                if not unique_id in unique_ids:
                    geometry = feature.GetGeometryRef()
                    location = Location(
                        unique_id=unique_id,
                        project=project,
                        area=self.area,
                        the_geom=fromstr(geometry.ExportToWkt()))
                    locations.append(location)
                    unique_ids.update(unique_id)
        Location.objects.bulk_create(locations)


    # TODO: the object model requires a major overhaul. Currently,
    # things are far from normalized: `ScheduledMeasurement` has
    # many - possibly conflicting - links to `Project`.
    def __save_scheduled_measurements(self, form_list):

        project = form_list[0].cleaned_data['project']
        contractor = form_list[1].cleaned_data['contractor']
        scheduled_measurements = []

        for key in form_list[2].cleaned_data['measurement_types']:

            mt = MeasurementType.objects.get(project=project,
                name=MEASUREMENT_TYPES[key]['name'])

            unique_ids = set(ScheduledMeasurement.objects.filter(
                project=project, contractor=contractor, measurement_type=mt).\
                values_list('location__unique_id', flat=True))

            difference = self.unique_ids - unique_ids

            for unique_id in difference:

                location = Location(unique_id=unique_id)
                scheduled_measurement = ScheduledMeasurement(
                    project=project, contractor=contractor,
                    measurement_type=mt, location=location)
                scheduled_measurements.append(scheduled_measurement)

        ScheduledMeasurement.objects.bulk_create(scheduled_measurements)


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
    """Foobar."""

    measurement_types = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        choices=[(k, v['choice']) for k, v in MEASUREMENT_TYPES.items()],
        label="Uit te voeren werkzaamheden")


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
        ext = os.path.splitext(value.name)[1]
        if ext.lower() not in self.exts:
            msg = "Verkeerd bestandsformaat."
            raise forms.ValidationError(msg)


class LocationForm(forms.Form):
    """Foobar."""

    dbf = ExtFileField(exts=[".dbf"])
#   prj = ExtFileField(exts=[".prj"])
    shp = ExtFileField(exts=[".shp"])
    shx = ExtFileField(exts=[".shx"])

    def clean(self):
        cleaned_data = super(LocationForm, self).clean()
        dbf = os.path.splitext(cleaned_data.get("dbf").name)[0]
        shp = os.path.splitext(cleaned_data.get("shp").name)[0]
        shx = os.path.splitext(cleaned_data.get("shx").name)[0]

        if dbf == shp == shx:
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

