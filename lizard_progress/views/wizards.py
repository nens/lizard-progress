"""Form-wizard views."""

import logging
import os
import osgeo.ogr
import re
import shutil
import tempfile

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.contrib.formtools.wizard.views import SessionWizardView
from django.contrib.gis.geos import fromstr
from django.contrib.gis.utils import LayerMapping
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import UploadedFile
from django.core.urlresolvers import reverse
from django.db import transaction
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template.defaultfilters import slugify
from django.utils.decorators import method_decorator

from lizard_progress.models import (Area, Hydrovak, Location,
    MeasurementType, SRID, ScheduledMeasurement)
from lizard_progress.views.upload import UploadShapefilesView


logger = logging.getLogger(__name__)

APP_LABEL = Area._meta.app_label


def location_shapefile_directory(project, contractor):
    return os.path.join(
        settings.BUILDOUT_DIR, 'var',
        APP_LABEL, project.slug,
        contractor.slug, 'locations')


def all_files_in(path, extension=None):
    for directory, dirnames, filenames in os.walk(path):
        for filename in filenames:
            if extension is None or filename.endswith(extension):
                yield os.path.join(directory, filename)


def newest_file_in(path, extension=None):
    mtime = lambda fn: os.stat(os.path.join(path, fn)).st_mtime
    filenames = sorted(all_files_in(path, extension), key=mtime)
    if filenames:
        return filenames[-1].encode('utf8')
    else:
        return None


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
            url = reverse('lizard_progress_newcontractor')
            msg = ('Volgende stap: <a href="%s" tabIndex="-1">' +
                'Opdrachtnemer toekennen aan een project</a>') % url
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
            msg = ('Het toekennen van opdrachtnemer "%s" aan project "%s" was '
                + 'succesvol.') % (contractor.name, contractor.project.name)
            messages.info(self.request, msg)
            url = reverse('lizard_progress_newactivities')
            msg = ('Volgende stap: <a href="%s" tabIndex="-1">' +
                'Werkzaamheden toewijzen aan een opdrachtnemer</a>') % url
            messages.info(self.request, msg)
            return HttpResponseRedirect('/progress/admin/')


class ActivitiesWizard(SessionWizardView):
    """Form wizard for creating new activities, i.e. `ScheduledMeasurements`.

    Usage of this wizard requires `lizard_progress.add_project` permission.
    """

    file_storage = OverwriteStorage(location=tempfile.mkdtemp())

    def __init__(self, *args, **kwargs):
        super(ActivitiesWizard, self).__init__(*args, **kwargs)
        self.location_codes = None
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
        has_shapefile = ((len(form_list) > 3) and
                         'shp' in form_list[3].cleaned_data)

        self.__save_measurement_types(form_list)

        if has_shapefile:
            self.__process_shapefile(form_list)
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
            msg = ('Het toewijzen van werkzaamheden aan opdrachtnemer '
                + '"%s" binnen project "%s" was succesvol.') % (
                contractor.name, contractor.project.name)
            messages.info(self.request, msg)
            url = reverse('lizard_progress_newhydrovakken')
            msg = ('Volgende stap: <a href="%s" tabIndex="-1">' +
                'Hydrovakken uploaden</a>') % url
            messages.info(self.request, msg)
            return HttpResponseRedirect('/progress/admin/')

    def __process_shapefile(self, form_list):
        """Process shapefile.

        Only one layer is assumed, which has the locations
        for activities (measurements, etc). Each location
        is represented by a unique id. Save the ids in a
        set for fast lookup.
        """
        location_codes = []
        shp = form_list[3].cleaned_data['shp']
        shapefile = osgeo.ogr.Open(str(shp.file.name))
        layer = shapefile.GetLayer(0)
        for feature_num in range(layer.GetFeatureCount()):
            feature = layer.GetFeature(feature_num)
            location_code = feature.GetField("ID_DWP")
            location_codes.append(location_code)
        self.location_codes = set(location_codes)

    @staticmethod
    def __save_measurement_types(form_list):
        """Save measurement types."""
        project = form_list[0].cleaned_data['project']
        for mtype in form_list[2].cleaned_data['measurement_types']:
            try:
                MeasurementType.objects.get(project=project, mtype=mtype)
            except MeasurementType.DoesNotExist:
                MeasurementType(project=project, mtype=mtype,
                    icon_missing=mtype.default_icon_missing,
                    icon_complete=mtype.default_icon_complete).save()

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

    def __save_locations(self, form_list):
        """Save locations."""
        project = form_list[0].cleaned_data['project']
        location_codes = set(Location.objects.filter(
            project=project).values_list('location_code', flat=True))
        locations = []
        shp = form_list[3].cleaned_data['shp']
        shapefile = osgeo.ogr.Open(str(shp.file.name))
        for layer_num in range(shapefile.GetLayerCount()):
            layer = shapefile.GetLayer(layer_num)
            for feature_num in range(layer.GetFeatureCount()):
                feature = layer.GetFeature(feature_num)
                location_code = feature.GetField("ID_DWP")
                if not location_code in location_codes:
                    geometry = feature.GetGeometryRef()
                    location = Location(
                        location_code=location_code,
                        project=project,
                        area=self.area,
                        the_geom=fromstr(geometry.ExportToWkt()))
                    locations.append(location)
                    location_codes.update(location_code)
        Location.objects.bulk_create(locations)

    # TODO: the object model requires a major overhaul. Currently,
    # things are far from normalized: `ScheduledMeasurement` has
    # many - possibly conflicting - links to `Project`.
    def __save_scheduled_measurements(self, form_list):
        """Save scheduled measurements."""

        # For reasons of performance, we want to use bulk_create.
        # However, it takes quite some preparation to make sure
        # that the transaction as a whole will succeed.

        project = form_list[0].cleaned_data['project']
        contractor = form_list[1].cleaned_data['contractor']
        scheduled_measurements = []

        # amtype = AvailableMeasurementType
        for amtype in form_list[2].cleaned_data['measurement_types']:
            # Skip measurement types that create their own scheduled
            # measurements as needed
            if not amtype.needs_scheduled_measurements:
                continue

            # mtype = MeasurementType
            mtype = MeasurementType.objects.get(project=project, mtype=amtype)

            # Measurements already scheduled. These need to
            # be excluded to make bulk_create successful.
            location_codes = set(ScheduledMeasurement.objects.filter(
                project=project, contractor=contractor,
                measurement_type=mtype).
                values_list('location__location_code', flat=True))

            # New location_codes, for which measurements need to
            # be scheduled, is the difference between two sets.
            difference = self.location_codes - location_codes

            # Get the corresponding `Location` objects.
            locations = Location.objects.filter(project=project,
                location_code__in=difference)

            # One `Location` for every `ScheduledMeasurement`.
            assert len(difference) == len(locations)

            # Create `ScheduledMeasurement` objects.
            for location in locations:
                scheduled_measurement = ScheduledMeasurement(
                    project=project, contractor=contractor,
                    measurement_type=mtype, location=location)
                scheduled_measurements.append(scheduled_measurement)

        # Finally, execute the bulk insert.
        ScheduledMeasurement.objects.bulk_create(scheduled_measurements)

    @staticmethod
    def __save_uploads(form_list):
        """Store uploaded files in their permanent location."""

        project = form_list[0].cleaned_data['project']
        contractor = form_list[1].cleaned_data['contractor']

        # The root directory.
        dst = location_shapefile_directory(project, contractor)

        # The root might not exist yet.
        if not os.path.exists(dst):
            os.makedirs(dst)

        # Create a unique subdirectory in the root.
        dst = tempfile.mkdtemp(prefix='upload-', dir=dst)

        # Copy the shapefile to the subdirectory.
        for _, value in form_list[3].cleaned_data.iteritems():
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


class ResultsWizard(SessionWizardView):
    """Form wizard for calculating/verifying final project results.

    Usage of this wizard requires `lizard_progress.add_project` permission.
    """

    @method_decorator(permission_required('lizard_progress.add_project'))
    def dispatch(self, *args, **kwargs):
        return super(ResultsWizard, self).dispatch(*args, **kwargs)

    def get_template_names(self):
        if self.steps.current == '2':
            return ["lizard_progress/results_last_step.html"]
        return ["lizard_progress/results.html"]

    def get_form_kwargs(self, step=None):
        form_kwargs = super(ResultsWizard, self).get_form_kwargs(step)
        if step == '0':
            form_kwargs['user'] = self.request.user
        elif step == '1':
            form_kwargs['project'] = \
                self.get_cleaned_data_for_step('0')['project']
        elif step == '2':
            form_kwargs['contractor'] = \
                self.get_cleaned_data_for_step('1')['contractor']
        return form_kwargs

    def done(self, form_list, **kwargs):
        if False:
            # For development purposes.
            return render_to_response('lizard_progress/done.html', {
                'form_data': [form.cleaned_data for form in form_list],
            })
        else:
            # TODO: this app should not depend on the hdsr site!
            from hdsr.metfile import generate_metfile
            from hdsr.mothershape import check_mothershape
            from hdsr_controle.realtech_hdsr.data_loader import controleren

            project = form_list[0].cleaned_data['project']
            contractor = form_list[1].cleaned_data['contractor']

            # The directory where final results will be stored.
            result_dir = os.path.join(settings.BUILDOUT_DIR, 'var', APP_LABEL,
                project.slug, contractor.slug, 'final_results')

            # Create it if necessary.
            if not os.path.exists(result_dir):
                os.makedirs(result_dir)

            # "Moedershape" / "Hydrovakkenshape"
            shapedir = UploadShapefilesView.get_directory(contractor)
            shapefilename = newest_file_in(shapedir, extension='.shp')

            if ScheduledMeasurement.objects.filter(
                    project=project,
                    contractor=contractor,
                    measurement_type__mtype__slug='dwarsprofiel').exists():
                metfilename = os.path.join(
                    result_dir, 'alle_dwarsprofielen.met')
                # Create one huge .met file.
                with open(metfilename, 'w') as metfile:
                    generate_metfile(project, contractor, metfile)

                # Realtech controle, klopt het aantal kuubs
                location_shape = newest_file_in(
                    location_shapefile_directory(project, contractor),
                    extension='.shp')

                if shapefilename and location_shape:
                    controleren(
                        shapefilename,
                        location_shape,
                        metfilename,
                        project.slug,
                        contractor.slug)

                    # The result file will have the same path as the
                    # 'mothershape', except with .zip as extension.
                    zipshapefile = re.sub('.shp$', '.zip', shapefilename)

                    # Move it to the result dir
                    result_path = os.path.join(
                            result_dir,
                            os.path.basename(zipshapefile))
                    if os.path.exists(result_path):
                        os.remove(result_path)
                    shutil.move(zipshapefile, result_path)

            if project.has_measurement_type('laboratorium_csv'):
                # Check the most recently uploaded 'mother' shapefile
                # against uploaded CSV files.  File
                # `laboratorium_check.txt` will have error messages.
                with open(
                    os.path.join(
                        result_dir,
                        'laboratorium_check.txt'), 'w') as txt_file:
                    check_mothershape(
                        project,
                        contractor,
                        shapefilename,
                        txt_file)

            # Redirect to downloads page.
            url = reverse('lizard_progress_downloadhomeview',
                kwargs={'project_slug': project.slug})

            return HttpResponseRedirect(url)
