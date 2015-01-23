# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.txt.
"""Views for the activity-specific pages.
"""

import datetime
import json
import logging
import os
import shutil
import tempfile

from django.contrib import messages
from django.http import Http404
from django.http import HttpResponse
from django.http import HttpResponseForbidden
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse

import osgeo.ogr

from ribxlib import parsers

from lizard_ui.layout import Action

from lizard_progress.views.views import KickOutMixin
from lizard_progress.views.views import ProjectsMixin
from lizard_progress.views.views import UiView

from lizard_progress import configuration
from lizard_progress import forms
from lizard_progress import models
from lizard_progress.util import dates
from lizard_progress.util import directories


logger = logging.getLogger(__name__)


class NoSuchFieldException(Exception):
    pass


class ActivityMixin(object):
    def dispatch(self, request, *args, **kwargs):
        if 'activity_id' in kwargs:
            try:
                self.activity_id = kwargs['activity_id']
                self.activity = models.Activity.objects.select_related().get(
                    pk=self.activity_id)
                del kwargs['activity_id']
            except models.Activity.DoesNotExist:
                pass

        if not self.activity or self.activity.project != self.project:
            raise Http404()

        return super(
            ActivityMixin, self).dispatch(request, *args, **kwargs)

    @property
    def user_is_activity_uploader(self):
        """User is an uploader if this organization is the contractor for
        this activity and user has role ROLE_UPLOADER."""
        return (self.user_has_uploader_role() and
                self.activity.contractor == self.organization)


class ActivityView(KickOutMixin, ProjectsMixin, ActivityMixin, UiView):
    """Base class for the Activity pages. It's a ProjectsView with
    self.activity set."""
    pass


class ActivityDashboard(ActivityView):
    active_menu = "activitydashboard"
    template_name = "lizard_progress/activity_dashboard.html"


class UploadHomeView(ActivityView):
    """The homepage for uploading files.

    Within a project, there are various files to be uploaded:
    measurements, shapefiles, reports, etc. This view is the
    starting point for a contractor who has to upload data.
    """
    template_name = "lizard_progress/upload_page.html"
    active_menu = "upload"

    def get(self, request, *args, **kwargs):
        if not self.activity.can_upload(request.user):
            return HttpResponseForbidden()

        return super(UploadHomeView, self).get(request, *args, **kwargs)

    @staticmethod
    def upload_dialog_url():
        """Returns URL to the file upload dialog."""
        return reverse('lizard_progress_uploaddialogview')

    def upload_measurement_url(self):
        """Returns URL to post measurements to."""
        return reverse('lizard_progress_uploadmeasurementsview',
                       kwargs=dict(
                           project_slug=self.project_slug,
                           activity_id=self.activity_id))

    def upload_reports_url(self):
        """Returns URL to post project reports to."""
        return reverse(
            'lizard_progress_uploadreportsview',
            kwargs={
                'project_slug': self.project_slug,
                'activity_id': self.activity_id
            })

    def upload_shapefiles_url(self):
        """Returns URL to post a project's (mother) shapefile to."""
        return reverse(
            'lizard_progress_uploadshapefilesview',
            kwargs={
                'project_slug': self.project_slug,
                'activity_id': self.activity_id
            })

    @property
    def breadcrumbs(self):
        """Breadcrumbs for this page."""
        crumbs = super(UploadHomeView, self).breadcrumbs

        crumbs.append(
            Action(
                description=("Uploads for {project}"
                             .format(project=self.project.name)),
                name="Upload",
                url=reverse(
                    'lizard_progress_uploadhomeview',
                    kwargs={'project_slug': self.project_slug,
                            'activity_id': self.activity_id})))

        return crumbs

    def files_ready(self):
        if not self.contractor:
            return []

        if not hasattr(self, '_files_ready'):
            self._files_ready = list(models.UploadedFile.objects.filter(
                project=self.project,
                contractor=self.contractor,
                ready=True))
        return self._files_ready

    def files_not_ready(self):
        if not self.contractor:
            return []

        if not hasattr(self, '_files_not_ready'):
            self._files_not_ready = list(models.UploadedFile.objects.filter(
                project=self.project,
                contractor=self.contractor,
                ready=False))
        return self._files_not_ready


class UploadedFilesView(UploadHomeView):
    """Return uploaded files as a JSON array."""
    def get(self, request, *args, **kwargs):
        return HttpResponse(
            json.dumps([
                uploaded_file.as_dict()
                for uploaded_file in
                models.UploadedFile.objects.filter(
                    activity=self.activity)]),
            content_type="application/json")


class PlanningView(ActivityView):
    template_name = 'lizard_progress/planning.html'
    active_menu = 'planning'

    def get(self, request, *args, **kwargs):
        if not hasattr(self, 'form'):
            self.form = self.get_form_class()()

        return super(PlanningView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.form = self.get_form_class()(request.POST, request.FILES)

        if not self.form.is_valid():
            return self.get(request, *args, **kwargs)

        if self.planning_uses_ribx:
            return self.post_ribx(request, *args, **kwargs)
        else:
            return self.post_shapefile(request, *args, **kwargs)

    def post_ribx(self, request, *args, **kwargs):
        ribxpath = self.__save_uploaded_ribx(request)

        locations_from_ribx = dict(
            self.__locations_from_ribx(ribxpath, request))
        if locations_from_ribx:
            existing_measurements = list(
                self.__existing_measurements())

            locations_with_measurements = set(
                existing_measurement.location.location_code
                for existing_measurement in existing_measurements)

            locations_to_keep = (set(locations_from_ribx) |
                                 locations_with_measurements)

            # Remove not needed scheduled measurements
            models.Location.objects.filter(
                activity=self.activity).exclude(
                location_code__in=locations_to_keep).delete()

            for location_code, (geom, loctype) in (
                    locations_from_ribx.iteritems()):
                location, created = models.Location.objects.get_or_create(
                    location_code=location_code,
                    activity=self.activity, defaults=dict(
                        location_type=loctype,
                        is_point=loctype != models.Location.LOCATION_TYPE_PIPE
                    ))
                location.the_geom = None
                location.plan_location(geom)

            return HttpResponseRedirect(
                reverse('lizard_progress_dashboardview', kwargs={
                    'project_slug': self.project.slug}))

        else:
            return HttpResponseRedirect(
                reverse('lizard_progress_planningview', kwargs={
                    'project_slug': self.project.slug,
                    'activity_id': self.activity_id
                }))

    def post_shapefile(self, request, *args, **kwargs):
        shapefilepath = self.__save_uploaded_files(request)

        try:
            locations_from_shapefile = dict(
                self.__locations_from_shapefile(shapefilepath))
        except NoSuchFieldException:
            messages.add_message(
                request, messages.ERROR,
                'Veld "{}" niet gevonden in de shapefile. '
                'Pas de shapefile aan,'
                'of geef een ander ID veld aan op het Configuratie scherm.'
                .format(self.location_id_field))

            return self.get(request, *args, **kwargs)

        if locations_from_shapefile:
            first_geom = locations_from_shapefile.values()[0]
            if 'POINT' not in first_geom:
                messages.add_message(
                    request, messages.ERROR,
                    'Shapefile moet punten bevatten.')
            return self.get(request, *args, **kwargs)

        existing_measurements = list(
            self.__existing_measurements())

        locations_with_measurements = set(
            existing_measurement.location.location_code
            for existing_measurement in existing_measurements)

        locations_to_keep = (set(locations_from_shapefile) |
                             locations_with_measurements)

        # Remove not needed scheduled measurements
        models.Location.objects.filter(
            activity=self.activity).exclude(
            location_code__in=locations_to_keep).delete()

        for location_code, geom in locations_from_shapefile.iteritems():
            location, created = models.Location.objects.get_or_create(
                location_code=location_code, activity=self.activity)
            if location.the_geom != geom:
                location.plan_location(geom)

        return HttpResponseRedirect(
            reverse('lizard_progress_dashboardview', kwargs={
                    'project_slug': self.project.slug}))

    def __save_uploaded_files(self, request):
        shapefilepath = directories.location_shapefile_path(
            self.activity)

        with open(shapefilepath + '.shp', 'wb+') as dest:
            for chunk in request.FILES['shp'].chunks():
                dest.write(chunk)
        with open(shapefilepath + '.dbf', 'wb+') as dest:
            for chunk in request.FILES['dbf'].chunks():
                dest.write(chunk)
        with open(shapefilepath + '.shx', 'wb+') as dest:
            for chunk in request.FILES['shx'].chunks():
                dest.write(chunk)

        return shapefilepath + '.shp'

    def __save_uploaded_ribx(self, request):
        ribxpath = directories.location_shapefile_path(
            self.activity) + '.ribx'

        with open(ribxpath, 'wb+') as dest:
            for chunk in request.FILES['ribx'].chunks():
                dest.write(chunk)

        return ribxpath

    @property
    def location_types(self):
        if not hasattr(self, '_location_types'):
            self._location_types = sorted(set(
                models.Location.objects.filter(
                    activity=self.activity).values_list(
                    'location_type', flat=True)))
        return self._location_types

    @property
    def shapefile_form(self):
        return forms.ShapefileForm()

    @property
    def location_id_field(self):
        return (
            configuration.get(self.activity, 'location_id_field')
            .strip().encode('utf8'))

    @property
    def planning_uses_ribx(self):
        return self.activity.measurement_type.planning_uses_ribx

    @property
    def date_planning(self):
        return self.activity.specifics().allow_planning_dates

    def get_form_class(self):
        if self.planning_uses_ribx:
            return forms.RibxForm
        else:
            return forms.ShapefileForm

    def __locations_from_shapefile(self, shapefilepath):
        """Get locations from shapefile and generate them as
        (location_code, WKT string) tuples."""

        if isinstance(shapefilepath, unicode):
            shapefilepath = shapefilepath.encode('utf8')
        shapefile = osgeo.ogr.Open(shapefilepath)

        location_id_field = self.location_id_field

        for layer_num in xrange(shapefile.GetLayerCount()):
            layer = shapefile.GetLayer(layer_num)
            for feature_num in xrange(layer.GetFeatureCount()):
                feature = layer.GetFeature(feature_num)

                try:
                    location_code = feature.GetField(
                        location_id_field).encode('utf8')
                except ValueError:
                    raise NoSuchFieldException()

                geometry = feature.GetGeometryRef().ExportToWkt()

                yield (location_code, geometry)

    def __locations_from_ribx(self, ribxpath, request):
        """Get pipe, manhole, drain locations from ribxpath and generate them
        as (piperef, (geom, location_type)) tuples.

        """

        ribx, errors = parsers.parse(
            ribxpath, parsers.Mode.PREINSPECTION)

        if errors:
            messages.add_message(
                request, messages.ERROR,
                'Er is niets opgeslagen vanwege fouten in het bestand:')

            msgs = [
                'Fout op regel {}: {}'.format(error['line'], error['message'])
                for error in errors]

            if len(msgs) > 20:
                msgs = msgs[:20] + [
                    'En nog {} andere fouten.'.format(len(msgs) - 20)]

            for message in msgs:
                messages.add_message(request, messages.ERROR, message)

            return

        messages.add_message(
            request, messages.INFO,
            'Bestand OK, {} pipes {} manholes {} drains'
            .format(len(ribx.pipes), len(ribx.manholes), len(ribx.drains)))

        for pipe in ribx.pipes:
            yield (pipe.ref, (pipe.geom, models.Location.LOCATION_TYPE_PIPE))

        for manhole in ribx.manholes:
            yield (manhole.ref,
                   (manhole.geom, models.Location.LOCATION_TYPE_MANHOLE))

        for drain in ribx.drains:
            yield (drain.ref,
                   (drain.geom, models.Location.LOCATION_TYPE_DRAIN))

        messages.add_message(
            request, messages.INFO,
            'Bestand OK, {} pipes {} manholes {} drains'
            .format(len(ribx.pipes), len(ribx.manholes), len(ribx.drains)))

    def __existing_measurements(self):
        return models.Measurement.objects.filter(
            location__activity=self.activity).select_related("location")


class ConnectActivityView(ActivityView):
    template_name = 'lizard_progress/planning_connect_activity.html'
    active_menu = 'planning'

    def get(self, request, *args, **kwargs):
        if not hasattr(self, 'form'):
            self.form = forms.ConnectActivityForm(self.activity)

        return super(ConnectActivityView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.form = forms.ConnectActivityForm(self.activity, request.POST)

        if not self.form.is_valid():
            return self.get(request, *args, **kwargs)

        self.activity.connect_to_activity(self.form.cleaned_data['activity'])

        return HttpResponseRedirect(reverse(
            'lizard_progress_planningview',
            kwargs={'project_slug': self.project_slug,
                    'activity_id': self.activity_id}))


class ConfigurationView(ActivityView):
    template_name = 'lizard_progress/activity_configuration_page.html'
    active_menu = "config"

    def config_options(self):
        config = configuration.Configuration(activity=self.activity)
        return list(config.options())

    def post(self, request, *args, **kwargs):
        redirect = HttpResponseRedirect(reverse(
            "lizard_progress_activity_configuration_view",
            kwargs={'project_slug': self.project_slug,
                    'activity_id': self.activity_id}))

        if not self.project.is_manager(self.user):
            return redirect

        for key in configuration.CONFIG_OPTIONS:
            option = configuration.CONFIG_OPTIONS[key]
            value_str = request.POST.get(key, '')
            try:
                value = option.translate(value_str)
                # No error, set it
                config = configuration.Configuration(activity=self.activity)
                config.set(option, value)
            except ValueError:
                pass

        return redirect


class UploadDateShapefiles(PlanningView):
    def post(self, request, *args, **kwargs):
        self.form = forms.ShapefileForm(request.POST, request.FILES)

        if not self.form.is_valid():
            messages.add_message(
                request, messages.ERROR,
                'Importeren van de shapefile is mislukt. '
                'Heeft u alle drie de bestanden verstuurd?')
        else:
            dirname = tempfile.mkdtemp()
            try:
                shp = self.__save_uploaded_files(request, dirname)
                location_type = kwargs['location_type']
                (planned, already_planned, skipped, notfound
                 ) = self.save_planned_dates(shp, location_type)

                if planned:
                    messages.add_message(
                        request, messages.INFO,
                        '{} locaties ingepland.'.format(planned))
                if already_planned:
                    messages.add_message(
                        request, messages.INFO,
                        '{} niet ingepland omdat ze al volledig zijn.'.format(
                            already_planned))
                if skipped:
                    messages.add_message(
                        request, messages.INFO,
                        '{} locaties overgeslagen omdat er geen '
                        'weeknummer ingevuld was.'.format(skipped))
                if notfound:
                    messages.add_message(
                        request, messages.INFO,
                        '{} locaties overgeslagen vanwege onbekende code.'
                        .format(planned))

            finally:
                shutil.rmtree(dirname)

        # We always redirect back to the planning view
        return HttpResponseRedirect(
            reverse('lizard_progress_planningview', kwargs={
                'project_slug': self.project.slug,
                'activity_id': self.activity_id
            }))

    def __save_uploaded_files(self, request, dirname):
        shapefilepath = os.path.join(dirname, 'tempshape')

        with open(shapefilepath + '.shp', 'wb+') as dest:
            for chunk in request.FILES['shp'].chunks():
                dest.write(chunk)
        with open(shapefilepath + '.dbf', 'wb+') as dest:
            for chunk in request.FILES['dbf'].chunks():
                dest.write(chunk)
        with open(shapefilepath + '.shx', 'wb+') as dest:
            for chunk in request.FILES['shx'].chunks():
                dest.write(chunk)

        return (shapefilepath + '.shp').encode('utf8')

    def save_planned_dates(self, shapefilepath, location_type):
        shapefile = osgeo.ogr.Open(shapefilepath)

        layer = shapefile.GetLayer(0)

        planned = 0
        already_planned = 0
        skipped = 0
        notfound = 0

        for feature_num in xrange(layer.GetFeatureCount()):
            feature = layer.GetFeature(feature_num)
            ref = feature.GetField(0)
            fields = feature.items()
            logger.debug(fields)
            if not fields.get(b'WEEKNUMMER'):
                # Not planned yet, OK
                skipped += 1
                continue

            try:
                location = models.Location.objects.get(
                    activity_id=self.activity_id,
                    location_code=ref,
                    location_type=location_type)
            except models.Location.DoesNotExist:
                # What to do...
                notfound += 1
                continue

            year = int(fields.get(b'JAAR') or datetime.datetime.today().year)
            week = int(fields.get(b'WEEKNUMMER'))

            # If no day is planned, use DAY 7 as the default -- that way
            # the work is not late as long as it is done inside that week.
            day = int(fields.get(b'DAGNUMMER') or '7')

            date = dates.weeknumber_to_date(year, week, day)

            if not location.complete:
                planned += 1
                location.plan_date(date)
            else:
                already_planned += 1

        return (planned, already_planned, skipped, notfound)
