# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

"""Form-wizard views."""

import logging
import os
import osgeo.ogr
import re
import shutil
import tempfile

from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.contrib.formtools.wizard.views import SessionWizardView
from django.contrib.gis.gdal import DataSource
from django.contrib.gis.geos import LineString
from django.contrib.gis.geos import MultiLineString
from django.contrib.gis.geos import fromstr
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import UploadedFile
from django.core.urlresolvers import reverse
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.utils.decorators import method_decorator

from lizard_ui.views import UiView

from lizard_progress.models import (Hydrovak, Location,
                                    MeasurementType,
                                    ScheduledMeasurement)
from lizard_progress.views.upload import UploadShapefilesView
from lizard_progress.util import directories
from lizard_progress import configuration

logger = logging.getLogger(__name__)

APP_LABEL = Hydrovak._meta.app_label


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


class ContractorWizard(UiView, SessionWizardView):
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
        contractor = form_list[0].save(commit=False)
        contractor.set_slug_and_save()

        if False:
            # For development purposes.
            return render_to_response('lizard_progress/done.html', {
                'form_data': [form.cleaned_data for form in form_list],
            })
        else:
            msg = ('Het toekennen van opdrachtnemer "%s" aan project "%s"' +
                   ' was succesvol.') % (contractor.organization.name,
                                         contractor.project.name)
            messages.info(self.request, msg)
            url = reverse('lizard_progress_newactivities')
            msg = ('Volgende stap: <a href="%s" tabIndex="-1">' +
                   'Werkzaamheden toewijzen aan een opdrachtnemer</a>') % url
            messages.info(self.request, msg)
            return HttpResponseRedirect(reverse('lizard_progress_admin'))


class ActivitiesWizard(UiView, SessionWizardView):
    """Form wizard for creating new activities, i.e. `ScheduledMeasurements`.

    Usage of this wizard requires `lizard_progress.add_project` permission.
    """

    file_storage = OverwriteStorage(location=tempfile.mkdtemp())

    def __init__(self, *args, **kwargs):
        super(ActivitiesWizard, self).__init__(*args, **kwargs)
        self.location_codes = None

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

        self.project = form_list[0].cleaned_data['project']
        self.__save_measurement_types(form_list)

        success = True
        if has_shapefile:
            success = self.__process_shapefile(form_list)

            if success:
                self.__save_locations(form_list)
                self.__save_scheduled_measurements(form_list)
                self.__save_uploads(form_list)

        if success:
            contractor = form_list[1].cleaned_data['contractor']
            msg = ('Het toewijzen van werkzaamheden aan ' +
                   'opdrachtnemer "%s" binnen project "%s" ' +
                   'was succesvol.') % (contractor.organization.name,
                                        contractor.project.name)
            messages.info(self.request, msg)
            url = reverse('lizard_progress_newhydrovakken')
            msg = ('Volgende stap: <a href="%s" tabIndex="-1">' +
                   'Hydrovakken uploaden</a>') % url
            messages.info(self.request, msg)
        return HttpResponseRedirect(reverse('lizard_progress_admin'))

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
            id_field_name = configuration.get(
                self.project, 'location_id_field')
            try:
                location_code = feature.GetField(id_field_name.encode('utf8'))
            except ValueError:
                messages.info(self.request,
                  ("Inlezen van de locaties mislukt! Het veld {name} "
                  "bestaat niet in de shapefile.").format(name=id_field_name))
                return False
            location_codes.append(location_code)
        self.location_codes = set(location_codes)
        return True

    def __save_measurement_types(self, form_list):
        """Save measurement types."""
        for mtype in form_list[2].cleaned_data['measurement_types']:
            try:
                MeasurementType.objects.get(
                    project=self.project, mtype=mtype)
            except MeasurementType.DoesNotExist:
                MeasurementType(
                    project=self.project, mtype=mtype,
                    icon_missing=mtype.default_icon_missing,
                    icon_complete=mtype.default_icon_complete).save()

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
                location_code = feature.GetField(
                    configuration.get(self.project, 'location_id_field')
                    .encode('utf8'))
                if not location_code in location_codes:
                    geometry = feature.GetGeometryRef()
                    location = Location(
                        location_code=location_code,
                        project=project,
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
        dst = directories.location_shapefile_dir(project, contractor)

        # Create a unique subdirectory in the root.
        dst = tempfile.mkdtemp(prefix='upload-', dir=dst)

        # Copy the shapefile to the subdirectory.
        for _, value in form_list[3].cleaned_data.iteritems():
            if isinstance(value, UploadedFile):
                shutil.copy(value.file.name, dst)


class HydrovakkenWizard(UiView, SessionWizardView):
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
        self.__save_uploads(form_list)
        success = self.__import_geoms(form_list)
        if success:
            project = form_list[0].cleaned_data['project']
            msg = ('Het uploaden van hydrovakken t.b.v. project "%s" '
                   + 'was succesvol.') % project.name
            messages.info(self.request, msg)
            url = reverse('lizard_progress_view',
                          kwargs={'project_slug': project.slug})
            msg = ('<a href="%s" tabIndex="-1">' +
                   'Naar de overzichtspagina van dit project</a>') % url
            messages.info(self.request, msg)

        return HttpResponseRedirect(reverse('lizard_progress_admin'))

    def __import_geoms(self, form_list):
        # TODO: `LayerMapping` offers no means of setting extra
        # model fields: only feature properties can be mapped.
        # To set the required `Project` foreign key, the pre_
        # save signal will be used in a fishy, by no means
        # robust way. Bear with me.
        success = True

        project = form_list[0].cleaned_data['project']
        shp = form_list[1].cleaned_data['shp']

        id_field_name = configuration.get(project, 'hydrovakken_id_field')

        datasource = DataSource(shp.file.name)
        layer = datasource[0]

        for feature in layer:
            if id_field_name in feature.fields:
                # The shape can contain both LineStrings and
                # MultiLineStrings - to be able to save both we
                # convert them all to multis
                geom = fromstr(feature.geom.ewkt)
                if isinstance(geom, LineString):
                    geom = MultiLineString(geom)

                hydrovak, created = Hydrovak.objects.get_or_create(
                    project=project,
                    br_ident=unicode(feature[id_field_name]),
                    defaults={'the_geom': geom})
                if not created:
                    hydrovak.the_geom = geom
                    hydrovak.save()
            else:
                logger.debug("id_field_name not present")
                logger.debug(feature.fields)

        return success

    @staticmethod
    def __save_uploads(form_list):
        """Store uploaded files in their permanent location."""

        # The root directory.
        project = form_list[0].cleaned_data['project']
        dst = directories.hydrovakken_dir(project)

        # Create a unique subdirectory in the root.
        dst = tempfile.mkdtemp(prefix='upload-', dir=dst)

        # Copy the shapefile to the subdirectory.
        for _, value in form_list[1].cleaned_data.iteritems():
            if isinstance(value, UploadedFile):
                shutil.copy(value.file.name, dst)


PROJECT = None


class ResultsWizard(UiView, SessionWizardView):
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
            from lizard_progress.util.metfile import generate_metfile
            from lizard_progress.mothershape import check_mothershape
            from hdsr_controle.realtech_hdsr.data_loader import controleren

            project = form_list[0].cleaned_data['project']
            contractor = form_list[1].cleaned_data['contractor']

            # The directory where final results will be stored.
            result_dir = directories.results_dir(project, contractor)

            # "Moedershape" / "Hydrovakkenshape"
            shapedir = UploadShapefilesView.get_directory(contractor)
            shapefilename = directories.newest_file_in(
                shapedir, extension='.shp')

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
                location_shape = directories.newest_file_in(
                    directories.location_shapefile_dir(project, contractor),
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
