# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

"""Views for the activity-specific pages.
"""

# Python 3 is coming
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from collections import defaultdict, namedtuple
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
from lizard_progress.util import geo
from lizard_progress.util import directories


logger = logging.getLogger(__name__)

# For the schedule check when checking if the day is specified and the
# schedule is less than this number of weeks ahead of the current week.
MINIMUM_WEEKS_DAY_CHECK = 2


class NoSuchFieldException(Exception):
    pass


class WrongGeometryTypeException(Exception):
    pass


class UploadException(Exception):
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
        """User is an uploader if the user has the role ROLE_UPLOADER and (1)
        this organization is the contractor for this activity, or (2) the
        project owning organisation is the same as this organization.
        """
        is_contracted_uploader = (
            self.user_has_uploader_role() and
            self.activity.contractor == self.organization)
        is_project_owner_in_simple_project = (
            self.activity.project.organization == self.organization and
            self.is_simple)
        return is_contracted_uploader or is_project_owner_in_simple_project

    @property
    def date_planning(self):
        return self.activity.specifics().allow_planning_dates

    def change_requests_menu_string(self):
        from lizard_progress.changerequests.models import Request

        n = len(Request.open_requests_for_profile(
                self.activity, self.profile))

        if n == 0:
            return ""
        else:
            return " ({n})".format(n=n)

    @property
    def show_planning_menu(self):
        return (self.user_is_manager() or (
            self.date_planning and self.user_is_activity_uploader))

    @property
    def show_date_planning_menu(self):
        return (self.date_planning and self.user_is_activity_uploader and
                not self.is_simple)


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

    @property
    def show_moedershapefile_button(self):
        """Temporary solution -- just don't show with anything RIBX
        related."""
        return ('ribx' not in
                self.activity.measurement_type.implementation_slug)


class UploadedFilesView(UploadHomeView):
    """Return uploaded files as a JSON array."""
    def get(self, request, *args, **kwargs):
        return HttpResponse(
            json.dumps([
                uploaded_file.as_dict()
                for uploaded_file in
                models.UploadedFile.objects.filter(
                    activity=self.activity).select_related(
                    'activity', 'activity__project')]),
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
            self.get_locations_from_ribx(
                self.activity, ribxpath,
                lambda msg: messages.add_message(request, messages.INFO, msg),
                lambda msg: messages.add_message(request, messages.ERROR, msg)
            )
        )

        if locations_from_ribx:
            existing_measurements = list(self.__existing_measurements())
            self.process_ribx_locations(
                self.activity, locations_from_ribx, ribxpath,
                existing_measurements)

            return HttpResponseRedirect(
                reverse('lizard_progress_dashboardview', kwargs={
                    'project_slug': self.project.slug}))

        else:
            return HttpResponseRedirect(
                reverse('lizard_progress_planningview', kwargs={
                    'project_slug': self.project.slug,
                    'activity_id': self.activity_id
                }))

    @staticmethod
    def process_ribx_locations(
            activity, locations_from_ribx, ribxpath, existing_measurements):
        # For drains
        care_about_ownership = activity.config_value(
            'ignore_drains_with_other_owners')

        locations_with_measurements = set(
            existing_measurement.location.location_code
            for existing_measurement in existing_measurements)

        # Remove not needed scheduled measurements
        models.Location.objects.filter(
            activity=activity).exclude(
            location_code__in=locations_with_measurements).delete()

        new_locations = [
            models.Location(
                location_code=location_code,
                activity=activity,
                location_type=loctype,
                is_point=loctype != models.Location.LOCATION_TYPE_PIPE,
                not_part_of_project=(
                    not_owned_by_organisation if care_about_ownership
                    else False),
                the_geom=(geo.osgeo_3d_line_to_2d_wkt(geom)
                          if loctype == models.Location.LOCATION_TYPE_PIPE
                          else geo.osgeo_3d_point_to_2d_wkt(geom)))

            for (location_code,
                 (geom, loctype, not_owned_by_organisation)) in
            locations_from_ribx.iteritems()

            if location_code not in locations_with_measurements
        ]

        models.Location.objects.bulk_create(new_locations)

        # Move RIBX file to project files
        newribxpath = os.path.join(
            directories.abs_project_files_dir(activity.project),
            os.path.basename(ribxpath)
        )
        if os.path.exists(newribxpath):
            os.remove(newribxpath)
        shutil.move(ribxpath, newribxpath)

    def post_shapefile(self, request, *args, **kwargs):
        shapefilepath = self.__save_uploaded_files(request)

        logger.debug("In post_shapefile")

        try:
            locations_from_shapefile = dict(
                self.__locations_from_shapefile(shapefilepath))
        except NoSuchFieldException:
            logger.debug("NoSuchFieldException")
            messages.add_message(
                request, messages.ERROR,
                'Veld "{}" niet gevonden in de shapefile. '
                'Pas de shapefile aan,'
                'of geef een ander ID veld aan op het Configuratie scherm.'
                .format(self.location_id_field))

            return self.get(request, *args, **kwargs)
        except WrongGeometryTypeException:
            logger.debug("WrongGeometryTypeException")
            messages.add_message(
                request, messages.ERROR,
                "Het geometrietype van de shapefile moet 'Point' zijn.")
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
        shapefilepath = directories.abs_location_shapefile_path(self.activity)

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
        ribxpath = os.path.join(
            directories.absolute(
                directories.rel_project_dir(self.activity.project)),
            request.FILES['ribx'].name
        )

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

            if (osgeo.ogr.GeometryTypeToName(layer.GetGeomType())
                    != b'Point'):
                raise WrongGeometryTypeException()

            for feature_num in xrange(layer.GetFeatureCount()):
                feature = layer.GetFeature(feature_num)

                try:
                    location_code = feature.GetField(
                        location_id_field).encode('utf8')
                except ValueError:
                    raise NoSuchFieldException()

                geometry = feature.GetGeometryRef().ExportToWkt()

                yield (location_code, geometry)

    def config_value(self, key):
        return self.activity.config_value(key)

    @staticmethod
    def get_locations_from_ribx(
            activity, ribxpath, msg_callback, error_msg_callback):
        """Get pipe, manhole, drain locations from ribxpath and generate them
        as (piperef, (geom, location_type)) tuples.

        """
        # Use these to check whether locations are inside extent
        min_x = activity.config_value('minimum_x_coordinate')
        max_x = activity.config_value('maximum_x_coordinate')
        min_y = activity.config_value('minimum_y_coordinate')
        max_y = activity.config_value('maximum_y_coordinate')
        # For drains
        eaq_code = activity.config_value('owner_organisation_eaq_code')

        ribx, errors = parsers.parse(ribxpath, parsers.Mode.PREINSPECTION)
        pipes = ribx.inspection_pipes + ribx.cleaning_pipes
        manholes = ribx.inspection_manholes + ribx.cleaning_manholes

        # First, if there are no errors, do our own error checking
        if not errors:
            errors = []
            for item in (pipes + ribx.drains + manholes):
                if item.geom is None:
                    errors.append({
                        'line': item.sourceline,
                        'message': 'Geen coördinaten gevonden.'
                    })
                    continue
                if not (min_x <= item.geom.GetX() <= max_x):
                    errors.append({
                        'line': item.sourceline,
                        'message': (
                            'X coördinaat niet tussen {} en {}.'
                            .format(min_x, max_x))
                        })
                    continue
                if not (min_y <= item.geom.GetY() <= max_y):
                    errors.append({
                        'line': item.sourceline,
                        'message': (
                            'Y coördinaat niet tussen {} en {}.'
                            .format(min_y, max_y))
                        })
                    continue

        if errors:
            error_msg_callback(
                'Er is niets opgeslagen vanwege fouten in het bestand:')

            msgs = [
                'Fout op regel {}: {}'.format(error['line'], error['message'])
                for error in errors]

            if len(msgs) > 20:
                msgs = msgs[:20] + [
                    'En nog {} andere fouten.'.format(len(msgs) - 20)]

            for message in msgs:
                error_msg_callback(message)

            return

        for pipe in pipes:
            logger.debug("PIPE: {} {}".format(pipe.ref, pipe.geom))
            yield (pipe.ref, (pipe.geom, models.Location.LOCATION_TYPE_PIPE,
                   False))

        for manhole in manholes:
            yield (manhole.ref,
                   (manhole.geom, models.Location.LOCATION_TYPE_MANHOLE,
                    False))

        for drain in ribx.drains:
            if eaq_code:
                owned_by_organisation = (drain.owner == eaq_code)
            else:
                owned_by_organisation = True

            yield (drain.ref,
                   (drain.geom, models.Location.LOCATION_TYPE_DRAIN,
                    not owned_by_organisation))

        msg_callback(
            'Bestand OK, {} pipes {} manholes {} drains'
            .format(len(pipes), len(manholes), len(ribx.drains)))

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
                info = self.save_planned_dates(shp, location_type)
            except UploadException:
                messages.add_message(
                    request, messages.ERROR,
                    "Uploaden is mislukt! De planning bevat een locatie die "
                    "is opgegeven voor deze of volgende week, maar waarbij "
                    "geen dag is gespecificeerd. Pas de planning aan en "
                    "probeer opnieuw.")
            else:
                if info.planned:
                    messages.add_message(
                        request, messages.INFO,
                        '{} locaties ingepland.'.format(info.planned))
                if info.already_planned:
                    messages.add_message(
                        request, messages.INFO,
                        '{} niet ingepland omdat ze al volledig zijn.'.format(
                            info.already_planned))
                if info.skipped_weeknumber:
                    messages.add_message(
                        request, messages.INFO,
                        '{} locaties overgeslagen omdat er geen '
                        'weeknummer ingevuld was.'.format(
                            info.skipped_weeknumber))
                if info.notfound:
                    messages.add_message(
                        request, messages.INFO,
                        '{} locaties overgeslagen vanwege onbekende code.'
                        .format(info.planned))
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
        """Register schedule data from the shapefile.

        Raises:
            UploadException: if you have a week scheduled within two weeks from
            the current week that does not have a day specified.
        """
        Info = namedtuple('Info', ['planned',
                                   'already_planned',
                                   'skipped_weeknumber',
                                   'notfound'])
        shapefile = osgeo.ogr.Open(shapefilepath)

        layer = shapefile.GetLayer(0)

        planned = 0
        already_planned = 0
        skipped_weeknumber = 0
        notfound = 0

        # This code tries to minimize the number of necessary queries.
        locations = {
            location_code: {
                'id': id,
                'planned_date': planned_date,
                'complete': complete
                }
            for location_code, id, planned_date, complete in
            models.Location.objects.filter(
                activity_id=self.activity_id,
                location_type=location_type,
                not_part_of_project=False)
            .values_list('location_code', 'id', 'planned_date', 'complete')
        }

        # Keys are dates, values are lists of ids of locations to update
        # to that date.
        locations_to_change = defaultdict(list)

        for feature_num in xrange(layer.GetFeatureCount()):
            feature = layer.GetFeature(feature_num)
            ref = feature.GetField(0)

            # Some editors (like my localc) change all fields to upper
            # case, some others (Bram's QGis) don't. Change them all
            # to upper case here.
            fields = {
                key.upper(): value
                for key, value in feature.items().items()
            }

            location = locations.get(ref)
            if location is None:
                # What to do...
                notfound += 1
                continue

            logger.debug(fields)
            try:
                week = int(fields.get(b'WEEKNUMMER'))
            except (ValueError, TypeError):
                week = None
            try:
                day = int(fields.get(b'DAGNUMMER'))
            except (ValueError, TypeError):
                day = None
            try:
                year = int(fields.get(b'JAAR'))
            except (ValueError, TypeError):
                year = datetime.datetime.today().year

            if not week:
                # Not planned yet, OK
                skipped_weeknumber += 1
                continue

            if not day:
                # If the week is within two weeks from the current week we
                # gotta check if the day is filled in.
                this_week = datetime.datetime.today().isocalendar()[1]
                if 0 <= week - this_week < MINIMUM_WEEKS_DAY_CHECK:
                    raise UploadException(
                        "The day MUST be present for a week scheduled within "
                        "two weeks.")
                else:
                    # If no day is planned, use DAY 7 as the default -- that
                    # way the work is not late as long as it is done inside
                    # that week.
                    day = 7

            date = dates.weeknumber_to_date(year, week, day)

            if not location['complete'] and location['planned_date'] != date:
                locations_to_change[date].append(location['id'])
                planned += 1
            else:
                already_planned += 1

        # Now, send an update query for each date that one or more locations
        # are now planned at.
        for date, ids in locations_to_change.iteritems():
            models.Location.objects.filter(
                id__in=ids).update(planned_date=date)

        return Info(planned=planned,
                    already_planned=already_planned,
                    skipped_weeknumber=skipped_weeknumber,
                    notfound=notfound)
