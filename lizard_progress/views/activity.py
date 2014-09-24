# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.txt.
"""Views for the activity-specific pages.
"""

import json

from django.http import Http404
from django.http import HttpResponse
from django.http import HttpResponseForbidden
from django.core.urlresolvers import reverse

from lizard_ui.layout import Action

from lizard_progress.views.views import KickOutMixin
from lizard_progress.views.views import ProjectsMixin
from lizard_progress.views.views import UiView

from lizard_progress import configuration
from lizard_progress import forms
from lizard_progress import models


class ActivityMixin(object):
    def dispatch(self, request, *args, **kwargs):
        if 'activity_id' in kwargs:
            try:
                self.activity_id = kwargs['activity_id']
                self.activity = models.Activity.objects.get(
                    pk=self.activity_id)
            except models.Activity.DoesNotExist:
                pass

        if not self.activity or self.activity.project != self.project:
            raise Http404()

        return super(
            ActivityMixin, self).dispatch(request, *args, **kwargs)


class ActivityView(KickOutMixin, ProjectsMixin, ActivityMixin, UiView):
    """Base class for the Activity pages. It's a ProjectsView with
    self.activity set."""
    pass


class ActivityDashboard(ActivityView):
    active_menu = "dashboard"
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
        return reverse('lizard_progress_uploadreportsview',
                       kwargs={'project_slug': self.project_slug})

    def upload_shapefiles_url(self):
        """Returns URL to post a project's (mother) shapefile to."""
        return reverse('lizard_progress_uploadshapefilesview',
                       kwargs={'project_slug': self.project_slug})

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

    def get(self, request, *args, **kwargs):
        if not hasattr(self, 'form'):
            self.form = forms.ShapefileForm()

        return super(PlanningView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.form = forms.ShapefileForm(request.POST)

        if not self.form.is_valid():
            return self.get(request, *args, **kwargs)

        contractor = models.Contractor.objects.get(slug=self.contractor_slug)
        amtype = models.AvailableMeasurementType.objects.get(
            slug=self.form.cleaned_data['mtype_slug'])

        mtype = models.MeasurementType.objects.get_or_create(
            mtype=amtype, project=self.project, defaults={
                'icon_missing': amtype.default_icon_missing,
                'icon_complete': amtype.default_icon_complete})[0]

        shapefilepath = self.__save_uploaded_files(request, contractor, amtype)
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

        existing_measurements = list(
            self.__existing_measurements(self.project, mtype, contractor))

        locations_with_measurements = set(
            existing_measurement.scheduled.location.location_code
            for existing_measurement in existing_measurements)

        locations_to_keep = (set(locations_from_shapefile) |
                             locations_with_measurements)

        # Remove not needed scheduled measurements
        models.ScheduledMeasurement.objects.filter(
            project=self.project, contractor=contractor,
            measurement_type=mtype).exclude(
            location__location_code__in=locations_to_keep).delete()

        for location_code, geom in locations_from_shapefile.iteritems():
            location, created = models.Location.objects.get_or_create(
                location_code=location_code, project=self.project)
            if location.the_geom != geom:
                location.the_geom = geom
                location.save()
            if location_code not in locations_with_measurements:
                models.ScheduledMeasurement.objects.get_or_create(
                    project=self.project, contractor=contractor,
                    measurement_type=mtype, location=location,
                    complete=False)

        return HttpResponseRedirect(
            reverse('lizard_progress_dashboardview', kwargs={
                    'project_slug': self.project.slug}))

    def __save_uploaded_files(self, request, contractor, amtype):
        shapefilepath = directories.location_shapefile_path(
            self.project, contractor, amtype)

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

    @property
    def location_id_field(self):
        return (
            configuration.get(self.project, 'location_id_field')
            .strip().encode('utf8'))

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

    def __existing_measurements(self, project, mtype, contractor):
        return models.Measurement.objects.filter(
            scheduled__project=project,
            scheduled__measurement_type=mtype,
            scheduled__contractor=contractor).select_related(
            "scheduled", "scheduled__location")
