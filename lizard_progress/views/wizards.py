"""Form-wizard views."""

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.contrib.formtools.wizard.views import SessionWizardView
from django.contrib.gis.geos import fromstr
from django.contrib.gis.utils import LayerMapping
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template.defaultfilters import slugify
from django.utils.decorators import method_decorator
from lizard_progress.forms import MEASUREMENT_TYPES
from lizard_progress.models import (Area, Hydrovak, Location,
    MeasurementType, SRID, ScheduledMeasurement, AvailableMeasurementType)
import os
import osgeo.ogr
import shutil
import tempfile

APP_LABEL = Area._meta.app_label


class OverwriteStorage(FileSystemStorage):
    """A `FileSystemStorage` class that overwrites existing files.

    Django's standard filesystem storage adds an underscore and
    a number to the filename if it already exists: it does not
    overwrite existing files. For shapefiles this is undesired
    behaviour, because it does not guarantee the individual
    `.dbf`, `.shp`, `.shx`, etc. files to have a common
    filename (apart from the extension).
    """

    def get_available_name(self, name):
        if self.exists(name):
            self.delete(name)
        return name


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


class ContractorWizard(SessionWizardView):
    """Form wizard for creating a new `Contractor`.

    Usage of this wizard requires `lizard_progress.add_project` permission.
    """

    @method_decorator(permission_required('lizard_progress.add_project'))
    def dispatch(self, *args, **kwargs):
        return super(ContractorWizard, self).dispatch(*args, **kwargs)

    def get_form_kwargs(self, step=None):
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


class ActivitiesWizard(SessionWizardView):
    """Form wizard for creating a new `Contractor`.

    Usage of this wizard requires `lizard_progress.add_project` permission.
    """

    file_storage = OverwriteStorage(location=tempfile.mkdtemp())

    def __init__(self, *args, **kwargs):
        super(ActivitiesWizard, self).__init__(*args, **kwargs)
        self.unique_ids = None
        self.area = None

    @method_decorator(permission_required('lizard_progress.add_project'))
    def dispatch(self, *args, **kwargs):
        return super(ActivitiesWizard, self).dispatch(*args, **kwargs)

    def get_form_kwargs(self, step=None):
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
        self.__save_uploads(form_list)
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
        """Process shapefile.

        Only one layer is assumed, which has the locations
        for activities (measurements, etc). Each location
        is represented by a unique id. Save the ids in a
        set for fast lookup.
        """
        unique_ids = []
        shp = form_list[3].cleaned_data['shp']
        shapefile = osgeo.ogr.Open(str(shp.file.name))
        layer = shapefile.GetLayer(0)
        for feature_num in range(layer.GetFeatureCount()):
            feature = layer.GetFeature(feature_num)
            unique_id = feature.GetField("ID_DWP")
            unique_ids.append(unique_id)
        self.unique_ids = set(unique_ids)

    # TODO: the object model requires a major overhaul. Currently,
    # a `MeasurementType` cannot exist without a `Project`.
    # A many-to-many relationship seems more appropriate.
    @staticmethod
    def __save_measurement_types(form_list):
        """Save measurement types."""
        project = form_list[0].cleaned_data['project']
        for key in form_list[2].cleaned_data['measurement_types']:
            if not MeasurementType.objects.filter(project=project,
                mtype__name=MEASUREMENT_TYPES[key]['name']).exists():
                mtype = AvailableMeasurementType.objects.get(
                    name=MEASUREMENT_TYPES[key]['name'])

                MeasurementType(
                    project=project,
                    mtype=mtype,
                    icon_missing=MEASUREMENT_TYPES[key]['icon_missing'],
                    icon_complete=MEASUREMENT_TYPES[key]['icon_complete']
                ).save()

    # Within a project, locations can be assigned to different
    # areas, for example `North`, `East`, `South`, and `West`.
    # This information cannot be automatically deduced from
    # the shape files yet. For that reason, we'll assign
    # all locations to a single `Area`.
    def __save_area(self, form_list):
        """Save area."""
        project = form_list[0].cleaned_data['project']
        self.area, _ = Area.objects.get_or_create(project=project,
            name=project.name, slug=project.slug)

    # TODO: the object model requires a major overhaul. Currently,
    # a specific `Location` can only be part of one `Project`.
    # A many-to-many relationship seems more appropriate.
    def __save_locations(self, form_list):
        """Save locations."""
        project = form_list[0].cleaned_data['project']
        unique_ids = set(Location.objects.filter(
            project=project).values_list('unique_id', flat=True))
        locations = []
        shp = form_list[3].cleaned_data['shp']
        shapefile = osgeo.ogr.Open(str(shp.file.name))
        for layer_num in range(shapefile.GetLayerCount()):
            layer = shapefile.GetLayer(layer_num)
            for feature_num in range(layer.GetFeatureCount()):
                feature = layer.GetFeature(feature_num)
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
        """Save scheduled measurements."""

        project = form_list[0].cleaned_data['project']
        contractor = form_list[1].cleaned_data['contractor']
        scheduled_measurements = []

        for key in form_list[2].cleaned_data['measurement_types']:

            mtype = MeasurementType.objects.get(project=project,
                name=MEASUREMENT_TYPES[key]['name'])

            unique_ids = set(ScheduledMeasurement.objects.filter(
                project=project, contractor=contractor,
                measurement_type=mtype).\
                values_list('location__unique_id', flat=True))

            difference = self.unique_ids - unique_ids

            for unique_id in difference:

                location = Location(unique_id=unique_id)
                scheduled_measurement = ScheduledMeasurement(
                    project=project, contractor=contractor,
                    measurement_type=mtype, location=location)
                scheduled_measurements.append(scheduled_measurement)

        ScheduledMeasurement.objects.bulk_create(scheduled_measurements)

    @staticmethod
    def __save_uploads(form_list):
        """Store uploaded files in their permanent location."""

        project = form_list[0].cleaned_data['project']
        contractor = form_list[1].cleaned_data['contractor']

        # The root directory.
        dst = os.path.join(settings.BUILDOUT_DIR, 'var',
            APP_LABEL, project.slug,
            contractor.slug, 'locations')

        # The root might not exist yet.
        if not os.path.exists(dst):
            os.makedirs(dst)

        # Create a unique subdirectory in the root.
        dst = tempfile.mkdtemp(prefix='upload-', dir=dst)

        # Copy the shapefile to the subdirectory.
        for _, value in form_list[1].cleaned_data.iteritems():
            if isinstance(value, UploadedFile):
                shutil.copy(value.file.name, dst)


class HydrovakkenWizard(SessionWizardView):
    """Form wizard for uploading a shapefile of hydrovakken.

    Usage of this wizard requires `lizard_progress.add_project` permission.
    """

    file_storage = OverwriteStorage(location=tempfile.mkdtemp())

    @method_decorator(permission_required('lizard_progress.add_project'))
    def dispatch(self, *args, **kwargs):
        return super(HydrovakkenWizard, self).dispatch(*args, **kwargs)

    def get_form_kwargs(self, step=None):
        form_kwargs = super(HydrovakkenWizard, self).get_form_kwargs(step)
        if step == '0':
            form_kwargs['user'] = self.request.user
        return form_kwargs

    def get_template_names(self):
        return ["lizard_progress/new_hydrovakken.html"]

    @transaction.commit_on_success
    def done(self, form_list, **kwargs):
        self.__import_geoms(form_list)
        self.__save_uploads(form_list)
        if False:
            # For development purposes.
            return render_to_response('lizard_progress/done.html', {
                'form_data': [form.cleaned_data for form in form_list],
            })
        else:
            project = form_list[0].cleaned_data['project']
            msg = ('Het uploaden van hydrovakken t.b.v. project "%s" '
                + 'was succesvol.') % project.name
            messages.info(self.request, msg)
            return HttpResponseRedirect('/progress/admin/')

    @staticmethod
    def __import_geoms(form_list):

        prj = form_list[1].cleaned_data.get('prj', None)
        shp = form_list[1].cleaned_data['shp']
        mapping = {'br_ident': 'BR_IDENT', 'the_geom': 'LINESTRING'}

        if prj:
            layer_mapping = LayerMapping(Hydrovak,
                shp.file.name, mapping)
        else:
            layer_mapping = LayerMapping(Hydrovak,
                shp.file.name, mapping,
                source_srs=SRID)

        try:
            # TODO: `LayerMapping` offers no means of setting extra
            # model fields: only feature properties can be mapped.
            # To set the required `Project` foreign key, the pre_
            # save signal will be used in a fishy, by no means
            # robust way. Bear with me.
            global PROJECT
            PROJECT = form_list[0].cleaned_data['project']
            layer_mapping.save(strict=True)
        finally:
            PROJECT = None

    @staticmethod
    def __save_uploads(form_list):
        """Store uploaded files in their permanent location."""

        # The root directory.
        project = form_list[0].cleaned_data['project']
        dst = os.path.join(settings.BUILDOUT_DIR, 'var',
            APP_LABEL, project.slug, 'hydrovakken')

        # The root might not exist yet.
        if not os.path.exists(dst):
            os.makedirs(dst)

        # Create a unique subdirectory in the root.
        dst = tempfile.mkdtemp(prefix='upload-', dir=dst)

        # Copy the shapefile to the subdirectory.
        for _, value in form_list[1].cleaned_data.iteritems():
            if isinstance(value, UploadedFile):
                shutil.copy(value.file.name, dst)


PROJECT = None


@receiver(pre_save, sender=Hydrovak)
def hydrovak_handler(sender, **kwargs):
    if PROJECT:
        hydrovak = kwargs['instance']
        if not hydrovak.pk:
            hydrovak.project = PROJECT
