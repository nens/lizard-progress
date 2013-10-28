# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.txt.
"""Views for the lizard-progress app. Includes:

MapView - can show projects as map layers
DashboardView - shows a project's dashboard, can show graphs per area and
                offers CSV files for download.
DashboardAreaView - a graph of the project's progress (hence "lizard-progress")
DashboardCsvView - a csv file view
protected_file_download - to download some uploaded files
ComparisonView - a listing of measurements made by more than one
                 contractor, that can be shown side by side
"""

import csv
import logging
import os
import platform
import shutil
import tempfile

import osgeo.ogr

from matplotlib import figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils import simplejson as json
from django.utils.translation import ugettext as _
from django.views.static import serve
from django import http
from django.contrib import auth

from lizard_map.matplotlib_settings import SCREEN_DPI
from lizard_map.views import AppView
from lizard_ui.layout import Action
from lizard_ui.views import UiView

from lizard_progress.layers import ProgressAdapter
from lizard_progress import models
from lizard_progress.models import Area
from lizard_progress.models import Contractor
from lizard_progress.models import Hydrovak
from lizard_progress.models import Location
from lizard_progress.models import MeasurementType
from lizard_progress.models import Project
from lizard_progress.models import ScheduledMeasurement
from lizard_progress.models import has_access
from lizard_progress.util import directories

from lizard_progress import configuration
from lizard_progress import forms

logger = logging.getLogger(__name__)


class ProjectsMixin(object):
    """Helper functions for working with projects in views"""
    project_slug = None
    project = None

    def dispatch(self, request, *args, **kwargs):
        self.request = request
        self.user = request.user
        self.profile = models.UserProfile.get_by_user(self.user)

        self.project_slug = kwargs.get('project_slug')
        if self.project_slug:
            self.project = get_object_or_404(Project, slug=self.project_slug)
            if has_access(request.user, self.project):
                self.has_full_access = all(
                    has_access(request.user, self.project, contractor)
                    for contractor in self.project.contractor_set.all())
            else:
                raise PermissionDenied()
        else:
            self.project = None

        return super(
            ProjectsMixin, self).dispatch(request, *args, **kwargs)

    def projects(self):
        """Returns a list of projects the current user has access to."""

        projects = []
        for project in Project.objects.all():
            if has_access(self.request.user, project):
                projects.append(project)
        return projects

    def organization(self):
        """Return organization name of current user."""
        return self.profile and self.profile.organization.name

    def user_can_upload_to_project(self):
        if not self.project:
            return False
        return self.project.can_upload(self.request.user)

    def user_is_uploader(self):
        """User is an upload if his organization is a contractor in
        this project and user has role ROLE_UPLOADER."""
        return (self.user_has_uploader_role() and
                (not self.project or models.Contractor.objects.filter(
                    project=self.project,
                    organization=self.profile.organization)
                 .exists()))

    def user_has_uploader_role(self):
        return (
            self.profile and
            self.profile.has_role(models.UserRole.ROLE_UPLOADER))

    def user_is_manager(self):
        """User is a manager if his organization owns this projects
        and user has the ROLE_MANAGER role."""
        return (self.user_has_manager_role() and
                (not self.project or
                 self.profile.organization == self.project.organization))

    def user_has_manager_role(self):
        return (
            self.profile and
            self.profile.has_role(models.UserRole.ROLE_MANAGER))

    def project_home_url(self):
        if not self.project_slug:
            return reverse('lizard_progress_projecten')

        if self.user_is_uploader():
            return reverse('lizard_progress_uploadhomeview',
                           kwargs={'project_slug': self.project_slug})
        else:
            return reverse('lizard_progress_dashboardview',
                           kwargs={'project_slug': self.project_slug})

    @property
    def breadcrumbs(self):
        """Returns a list of breadcrumbs to this project."""
        crumbs = [
            Action(
                description="Home",
                name="Home",
                url="/")]

        if self.project:
            crumbs.append(
                Action(
                    description=self.project.name,
                    name=self.project.name,
                    url=self.project_home_url()))

        return crumbs


class KickOutMixin(object):
    def dispatch(self, request, *args, **kwargs):
        """You can only get here if you are part of some organization.
        So admin can't."""
        self.organization = models.Organization.get_by_user(
            request.user)
        if not self.organization:
            auth.logout(request)
            return http.HttpResponseRedirect('/')

        return super(KickOutMixin, self).dispatch(request, *args, **kwargs)

    @property
    def site_actions(self):
        actions = super(KickOutMixin, self).site_actions

        actions[0:0] = [
            Action(
                icon='icon-briefcase',
                name=self.organization,
                description=(_("Your current organization")))
            ]

        return actions


class ProjectsView(KickOutMixin, ProjectsMixin, UiView):
    """Displays a list of projects to choose from."""
    template_name = "lizard_progress/projects.html"


class View(KickOutMixin, ProjectsMixin, AppView):
    """The app's root, shows a choice of projects, or a choice of
    dashboard / upload / map layer pages if a project is chosen."""

    template_name = 'lizard_progress/home.html'


class MapView(View):
    """View that can show a project's locations as map layers."""
    template_name = 'lizard_progress/map.html'

    def available_layers(self):
        """List of layers available to draw. Per contractor per area,
        there is one layer for each measurement type and one layer
        that shows all measurement types simultaneously. If the user
        has access to that contractor's data."""

        logger.debug("Available layers:")
        layers = []
        for contractor in self.project.contractor_set.all():
            if has_access(self.request.user, self.project, contractor):
                mtype_layers = []
                for measurement_type in self.project.measurementtype_set.all():
                    if (measurement_type.mtype.can_be_displayed
                        and contractor.show_measurement_type(
                            measurement_type)):
                        mtype_layers.append({
                                'name': '%s %s %s' %
                                (self.project.name,
                                 contractor.name,
                                 measurement_type.name),
                                'adapter': 'adapter_progress',
                                'json': json.dumps({
                                        "contractor_slug":
                                            contractor.slug,
                                        "measurement_type_slug":
                                            measurement_type.slug,
                                        "project_slug":
                                            self.project.slug}),
                                })

                if len(mtype_layers) > 1:
                    layers.append({
                            'name': '%s %s Alle metingen'
                            % (self.project.name, contractor.name),
                            'adapter': 'adapter_progress',
                            'json': json.dumps({
                                    "contractor_slug":
                                        contractor.slug,
                                    "project_slug":
                                        self.project.slug})
                            })
                layers += mtype_layers

        if Hydrovak.objects.filter(project=self.project).exists():
            layers.append({
                'name': 'Hydrovakken {projectname}'
                .format(projectname=self.project.name),
                'adapter': 'adapter_hydrovak',
                'json': json.dumps({"project_slug": self.project_slug})
            })

        return layers

    @property
    def content_actions(self):
        """Hide everything but the zoom to start location action"""
        return [action for action in
                super(MapView, self).content_actions
                if 'load-default-location' in action.klass]

    @property
    def breadcrumbs(self):
        """Breadcrumbs for this page."""

        crumbs = super(MapView, self).breadcrumbs

        crumbs.append(
            Action(
                name="Kaartlagen",
                description=("De kaartlagen van {project} in Lizard"
                             .format(project=self.project.name)),
                url=reverse('lizard_progress_mapview',
                            kwargs={'project_slug': self.project_slug})))

        return crumbs


class ComparisonView(View):
    """View that can show measurement types of this project, and if
    one is chosen, a sorted list of locations with more than one
    contractor."""

    template_name = 'lizard_progress/comparison.html'

    def dispatch(self, request, *args, **kwargs):
        """Check access (user needs to be able to read data of all
        contractors), and find the current measurement type, if any."""

        self.mtype_slug = kwargs.get('mtype_slug', None)

        result = super(ComparisonView, self).dispatch(request, *args, **kwargs)

        for contractor in self.project.contractor_set.all():
            if not has_access(request.user, self.project, contractor):
                raise PermissionDenied()

        return result

    def crumbs(self):
        """Breadcrumb for this page."""
        crumbs = super(ComparisonView, self).crumbs()

        crumbs.append({
                'url': self.comparison_url(),
                'description': 'Vergelijking',
                'title': '%s vergelijking' % (self.project.name,)
                })

        return crumbs

    @property
    def measurement_type(self):
        if self.mtype_slug is not None:
            return MeasurementType.objects.get(
                project=self.project,
                mtype__slug=self.mtype_slug)
        else:
            return None

    def measurement_types(self):
        """Return available measurement types."""

        measurement_types = self.project.measurementtype_set.all()
        logger.debug("Hrm.")
        logger.debug(measurement_types)
        return measurement_types

    def measurement_types_urls(self):
        return [(measurement_type,
                 reverse(
                    'lizard_progress_comparisonview2',
                    kwargs={
                        'project_slug': self.project.slug,
                        'mtype_slug': measurement_type.slug,
                        }))
                for measurement_type in self.measurement_types()]

    def locations_to_compare(self):
        """Locations that have more than scheduled measurements by
        more than one contractor, for this measurement type"""

        measurement_type = self.measurement_type

        if not measurement_type or not measurement_type.id:
            return ()

        # We're looking for locations in this project where the number
        # of distinct contractors that have a completed scheduled
        # measurement of this measurement type on that location is
        # greater than 1.

        # As far as I can see, that beats Django's ORM and we need to
        # use SQL.
        locations = (
            Location.objects.filter(project=self.project).
            extra(where=["""
         (SELECT
            COUNT(
              DISTINCT lizard_progress_scheduledmeasurement.contractor_id)
          FROM
            lizard_progress_scheduledmeasurement
          WHERE
            lizard_progress_scheduledmeasurement.location_id =
              lizard_progress_location.id
          AND
            lizard_progress_scheduledmeasurement.complete='t'
          AND
            lizard_progress_scheduledmeasurement.measurement_type_id=%d
          ) > 1
         """ % measurement_type.id]).
            order_by('location_code').
            all())

        return [(location,
                 self.comparison_popup_url(measurement_type, location))
                for location in locations]

    def comparison_popup_url(self, measurement_type, location):
        """Returns URL to this project's Comparison view"""
        return reverse(
            'lizard_progress_comparisonpopup',
            kwargs={
                'project_slug': self.project_slug,
                'mtype_slug': measurement_type.slug,
                'location_code': location.location_code,
                }
            )


class ComparisonPopupView(View):
    template_name = 'lizard_progress/comparison_popup.html'

    def dispatch(self, request, *args, **kwargs):
        """Check access (user needs to be able to read data of all
        contractors), find current measurement type and location."""

        self.mtype_slug = kwargs.get('mtype_slug', None)
        self.measurement_type = MeasurementType.objects.get(
            project=self.project,
            mtype__slug=self.mtype_slug)

        self.location_code = kwargs.get('location_code', None)
        self.location = Location.objects.get(
            project=self.project,
            location_code=self.location_code)

        result = super(ComparisonPopupView, self).dispatch(
            request, *args, **kwargs)

        for contractor in self.project.contractor_set.all():
            if not has_access(request.user, self.project, contractor):
                raise PermissionDenied()

        return result

    def contractors(self):
        """Return the contractors that have a complete measurement at
        this location"""

        contractors = set()

        scheduled_measurements = (
            ScheduledMeasurement.objects.
            filter(project=self.project).
            filter(measurement_type=self.measurement_type).
            filter(location=self.location).
            filter(complete=True))

        for sm in scheduled_measurements:
            contractors.add(sm.contractor)

        return sorted(contractors,
                      cmp=lambda a, b: cmp(a.name, b.name))

    def contractor_html(self):
        """Perform lizard-map-ish magic to get the same HTML as normal
        popups do."""
        htmls = []

        class FakeWorkspaceItem(object):
            adapter_class = 'adapter_progress'

            def __init__(self, layer_arguments):
                self.adapter_layer_json = json.dumps(layer_arguments)

            def _url_arguments(self, identifiers):
                """for img_url, csv_url"""

                from lizard_map.adapter import adapter_serialize

                layer_json = self.adapter_layer_json.replace('"', '%22')
                url_arguments = [
                    'adapter_layer_json=%s' % layer_json, ]
                url_arguments.extend([
                        'identifier=%s' % adapter_serialize(
                            identifier) for identifier in identifiers])
                return url_arguments

            def url(self, url_name, identifiers, extra_kwargs=None):
                """fetch url to adapter (img, csv, ...)

                example url_name: "lizard_map_adapter_image"
                """
                kwargs = {'adapter_class': 'adapter_progress'}
                if extra_kwargs is not None:
                    kwargs.update(extra_kwargs)
                url = reverse(
                    url_name,
                    kwargs=kwargs,
                    )
                url += '?' + '&'.join(self._url_arguments(identifiers))
                return url

        for contractor in self.contractors():
            try:
                layer_arguments = {
                    'project_slug': self.project.slug,
                    'contractor_slug': contractor.slug,
                    'measurement_type_slug': self.measurement_type.slug,
                    }

                workspace_item = FakeWorkspaceItem(layer_arguments)

                adapter = ProgressAdapter(
                    workspace_item=workspace_item,
                    layer_arguments=layer_arguments,
                    )

            except Exception as e:
                logger.critical("Adapter exception: " + str(e))

            scheduled_measurements = (
                ScheduledMeasurement.objects.
                filter(project=self.project).
                filter(location=self.location).
                filter(contractor=contractor).
                filter(measurement_type=self.measurement_type))

            sm_ids = [{
                    'scheduled_measurement_id': sm.id,
                    } for sm in scheduled_measurements]

            try:
                htmls.append(adapter.html(identifiers=sm_ids))
            except Exception as e:
                logger.critical("HTML exception: " + str(e))

        return htmls


class DashboardView(ProjectsView):
    """Show the dashboard page. The page offers a popup per area per
    contractor, if the user has access, and also downloads to CSV
    files."""

    template_name = 'lizard_progress/dashboard.html'
    active_menu = "dashboard"

    @property
    def breadcrumbs(self):
        """Breadcrumbs for this page."""

        crumbs = super(DashboardView, self).breadcrumbs

        crumbs.append(
            Action(
                name="Dashboard",
                description=("{project} dashboard"
                             .format(project=self.project.name)),
                url=reverse(
                    'lizard_progress_dashboardview',
                    kwargs={'project_slug': self.project_slug})))

        return crumbs

    def areas(self):
        """The areas for which to show popup links. Shows each area
        for each contractor the user has access to."""

        areas = []
        for contractor in Contractor.objects.filter(project=self.project):
            if has_access(self.request.user, self.project, contractor):
                for area in Area.objects.filter(project=self.project):
                    areas.append((contractor, area,
                                  reverse('lizard_progress_dashboardareaview',
                                          kwargs={
                                    'contractor_slug': contractor.slug,
                                    'project_slug': self.project.slug,
                                    'area_slug': area.slug})))

        return areas


class DashboardAreaView(View):
    """Shows Dashboard popup for one area."""

    template_name = "lizard_progress/dashboard_content.html"

    def dispatch(self, request, *args, **kwargs):
        """Get objects project, area and contractor from the request,
        404 if they are not found. Check if the user has access."""

        self.project_slug = kwargs.get('project_slug', None)
        self.project = get_object_or_404(Project, slug=self.project_slug)
        self.area_slug = kwargs.get('area_slug', None)
        if self.area_slug:
            self.area = get_object_or_404(Area,
                                          project=self.project,
                                          slug=self.area_slug)
        self.contractor_slug = kwargs.get('contractor_slug', None)
        self.contractor = get_object_or_404(Contractor,
                                            project=self.project,
                                            slug=self.contractor_slug)

        if not has_access(request.user, self.project, self.contractor):
            raise PermissionDenied()

        return (super(DashboardAreaView, self).
                dispatch(request, *args, **kwargs))

    def graph_url(self):
        """Url to the actual graph."""
        return reverse('lizard_progress_dashboardgraphview', kwargs={
                'project_slug': self.project.slug,
                'contractor_slug': self.contractor.slug,
                'area_slug': self.area.slug})


class DashboardCsvView(DashboardAreaView):
    """Returns a CSV file for a contractor and measurement type."""

    template_name = "lizard_progress/project_progress.csv"

    def clean_filename(self, filename):
        """
        Filenames are stored with an elaborate timestamp:
        20120301-134855-0-pilot_peilschalen.csv

        For the CSV file, we want to show an original filename
        followed by the date in parentheses:
        pilot_peilschalen.csv (2012-03-01)

        In case of any errors or surprises, return the basename of the
        original.
        """

        filename = os.path.basename(filename)

        parts = filename.split('-')
        if len(parts) < 4:
            return filename

        datestr, _timestr, _seqstr = parts[:3]
        orig_filename = '-'.join(parts[3:])

        if len(datestr) != 8:
            return filename

        return "%s (%s-%s-%s)" % (orig_filename, datestr[:4],
                                  datestr[4:6], datestr[6:])

    def get(self, request, *args, **kwargs):
        """Returns a CSV file for this contractor and measurement
        type."""

        # Setup HttpResponse and a CSV writer
        response = http.HttpResponse(content_type="text/csv")
        writer = csv.writer(response)

        filename = '%s_%s.csv' % (self.project.slug, self.contractor.slug)

        response['Content-Disposition'] = ('attachment; filename=%s' %
                                           (filename,))

        # Get measurement types, locations
        measurement_types = sorted(
            self.project.measurementtype_set.all(),
            cmp=lambda a, b: cmp(a.name, b.name))

        locations = sorted(
            self.project.location_set.all(),
            cmp=lambda a, b: cmp(a.location_code, b.location_code))

        # Write header row
        row1 = ['ID']
        for mtype in measurement_types:
            row1.append(mtype.name)
        writer.writerow(row1)

        # Write rest of the rows
        for l in locations:
            # Are there any scheduled measurements for this contractor
            # at this location? Otherwise skip it.
            if (ScheduledMeasurement.objects.filter(
                    project=self.project, contractor=self.contractor,
                    location=l).count()) == 0:
                continue

            # Row has the location's id first, then some information
            # per measurement type.
            row = [l.location_code]
            for mtype in measurement_types:
                try:
                    scheduled = ScheduledMeasurement.objects.get(
                        project=self.project, contractor=self.contractor,
                        location=l, measurement_type=mtype)
                except ScheduledMeasurement.DoesNotExist:
                    # This measurement type wasn't scheduled here -
                    # empty cell.
                    row.append('')
                    continue

                if scheduled.complete:
                    # Nice sorted list of filenames and dates.
                    filenames = [self.clean_filename(measurement.filename)
                                 for measurement in
                                 scheduled.measurement_set.all()]

                    # Case insensitive sort
                    filenames = sorted(
                        filenames,
                        cmp=lambda a, b: cmp(a.lower(), b.lower()))

                    row.append(', '.join(filenames))
                else:
                    # Although it is possible that there is some data already
                    # (e.g., one photo already uploaded while the measurement
                    # needs two to be complete), for simplicity we simply say
                    # that the whole measurement isn't there yet.
                    row.append('Nog niet aanwezig')

            writer.writerow(row)

        # Return
        return response


class ScreenFigure(figure.Figure):
    """A convenience class for creating matplotlib figures.

    Dimensions are in pixels. Float division is required,
    not integer division!
    """
    def __init__(self, width, height):
        super(ScreenFigure, self).__init__(dpi=SCREEN_DPI)
        self.set_size_pixels(width, height)
        self.set_facecolor('white')

    def set_size_pixels(self, width, height):
        """Set figure size in pixels"""
        dpi = self.get_dpi()
        self.set_size_inches(width / dpi, height / dpi)


@login_required
def dashboard_graph(request, project_slug, contractor_slug,
                    area_slug, *args, **kwargs):
    """Show the work in progress per area in pie charts.

    A single PNG image is returned as a response.
    """
    project = get_object_or_404(Project, slug=project_slug)
    area = get_object_or_404(Area, project=project, slug=area_slug)
    contractor = get_object_or_404(Contractor, project=project,
                                   slug=contractor_slug)

    if not has_access(request.user, project, contractor):
        raise PermissionDenied()

    fig = ScreenFigure(600, 350)  # in pixels
    fig.text(
        0.5, 0.85,
        ('Uitgevoerde werkzaamheden {contractor}'
         .format(contractor=contractor.organization.name)),
        fontsize=14, ha='center')
    fig.subplots_adjust(left=0.05, right=0.95)  # smaller margins
    y_title = -0.2  # a bit lower

    def autopct(pct):
        "Convert absolute numbers into percentages."
        total = done + todo
        return "%d" % int(round(pct * total / 100.0))

    def subplot_generator(images):
        """Yields matplotlib subplot placing numbers"""

        # Maybe we can make this smarter later on
        rows = 1
        cols = images

        start = 100 * rows + 10 * cols

        n = 0
        while n < images:
            n += 1
            yield start + n

    mtypes = project.measurementtype_set.all()
    subplots = subplot_generator(len(mtypes))

    for mtype in mtypes:
        # Profiles to be measured
        total = (ScheduledMeasurement.objects.
                 filter(project=project,
                        contractor=contractor,
                        measurement_type=mtype,
                        location__area=area).count())

        # Measured profiles
        done = ScheduledMeasurement.objects.filter(project=project,
                                                   contractor=contractor,
                                                   measurement_type=mtype,
                                                   location__area=area,
                                                   complete=True).count()

        todo = total - done
        x = [done, todo]
        labels = ['Wel', 'Niet']
        colors = ['#50CD34', '#FE6535']
        ax = fig.add_subplot(subplots.next())
        ax.pie(x, labels=labels, colors=colors, autopct=autopct)
        ax.set_title(mtype.name, y=y_title)
        ax.set_aspect('equal')  # circle

    # Create the response
    response = http.HttpResponse(content_type='image/png')
    canvas = FigureCanvas(fig)
    canvas.print_png(response)
    return response


@login_required
def protected_file_download(request, project_slug, contractor_slug,
                                   measurement_type_slug, filename):
    """
    We need our own file_download view because contractors can only see their
    own files, and the URLs of other contractor's files are easy to guess.

    Copied and adapted from deltaportaal, which has a more generic
    example, in case you're looking for one. It is for Apache.

    The one below works for both Apache (untested) and Nginx.  I used
    the docs at http://wiki.nginx.org/XSendfile for the Nginx
    configuration.  Basically, Nginx serves /protected/ from the
    document root at BUILDOUT_DIR+'var', and we x-accel-redirect
    there. Also see the bit of nginx conf in hdsr's etc/nginx.conf.in.
    """

    project = get_object_or_404(Project, slug=project_slug)
    contractor = get_object_or_404(Contractor, slug=contractor_slug,
                                   project=project)
    mtype = get_object_or_404(
        MeasurementType, mtype__slug=measurement_type_slug,
        project=project)

    logger.debug("Incoming programfile request for %s", filename)

    if '/' in filename or '\\' in filename:
        # Trickery?
        logger.warn("Returned Forbidden on suspect path %s" % (filename,))
        return http.HttpResponseForbidden()

    if not has_access(request.user, project, contractor):
        logger.warn("Not allowed to access %s", filename)
        return http.HttpResponseForbidden()

    file_path = directories.make_uploaded_file_path(
        directories.BASE_DIR, project, contractor,
        mtype, filename)
    nginx_path = directories.make_uploaded_file_path(
        '/protected', project, contractor,
        mtype, filename)

    # This is where the magic takes place.
    response = http.HttpResponse()
    response['X-Sendfile'] = file_path  # Apache
    response['X-Accel-Redirect'] = nginx_path  # Nginx

    # Unset the Content-Type as to allow for the webserver
    # to determine it.
    response['Content-Type'] = ''

    # Only works for Apache and Nginx, under Linux right now
    if settings.DEBUG or not platform.system() == 'Linux':
        logger.debug(
            "With DEBUG off, we'd serve the programfile via webserver: \n%s",
            response)
        return serve(request, file_path, '/')
    return response


class NewProjectView(ProjectsView):
    template_name = "lizard_progress/newproject.html"

    @models.UserRole.check(models.UserRole.ROLE_MANAGER)
    def dispatch(self, request, *args, **kwargs):
        if request.method == 'POST':
            self.form = forms.NewProjectForm(request.POST)
        else:
            self.form = forms.NewProjectForm()

        return super(NewProjectView, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if not self.form.is_valid():
            return self.get(request, *args, **kwargs)

        profile = models.UserProfile.get_by_user(request.user)
        organization = profile.organization

        project = models.Project(
            name=self.form.cleaned_data['name'],
            organization=organization)
        project.set_slug_and_save()

        for contractor in self.form.cleaned_data['contractors']:
            c = models.Contractor(
                project=project,
                organization=contractor)
            c.set_slug_and_save()

        for mtype in self.form.cleaned_data['mtypes']:
            c = models.MeasurementType.objects.create(
                project=project,
                mtype=mtype)

        return HttpResponseRedirect(
            reverse('lizard_progress_project_configuration_view',
                    kwargs={'project_slug': project.slug}))


class PlanningView(ProjectsView):
    template_name = 'lizard_progress/planning.html'

    def dispatch(self, request, *args, **kwargs):
        if request.method == 'GET':
            self.form = forms.ShapefileForm()
        elif request.method == 'POST':
            self.form = forms.ShapefileForm(request.POST, request.FILES)

        self.contractor_slug = kwargs.pop('contractor_slug', None)
        self.mtype_slug = kwargs.pop('mtype_slug', None)

        return super(PlanningView, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if not self.form.is_valid():
            return self.get(request, *args, **kwargs)

        contractor = models.Contractor.objects.get(slug=self.contractor_slug)
        amtype = models.AvailableMeasurementType.objects.get(
            slug=self.mtype_slug)

        mtype = models.MeasurementType.objects.get_or_create(
            mtype=amtype, project=self.project)[0]

        tempdir = self.__save_uploaded_files(request)
        locations_from_shapefile = dict(
            self.__locations_from_shapefile(tempdir))
        self.__remove_tempdir(tempdir)

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

    def __save_uploaded_files(self, request):
        tempdir = tempfile.mkdtemp()

        with open(os.path.join(tempdir, 'shapefile.shp'), 'wb+') as dest:
            for chunk in request.FILES['shp'].chunks():
                dest.write(chunk)
        with open(os.path.join(tempdir, 'shapefile.dbf'), 'wb+') as dest:
            for chunk in request.FILES['dbf'].chunks():
                dest.write(chunk)
        with open(os.path.join(tempdir, 'shapefile.shx'), 'wb+') as dest:
            for chunk in request.FILES['shx'].chunks():
                dest.write(chunk)

        return tempdir

    def __remove_tempdir(self, tempdir):
        shutil.rmtree(tempdir)

    def __locations_from_shapefile(self, tempdir):
        """Get locations from shapefile and generate them as
        (location_code, WKT string) tuples."""

        shapefile = osgeo.ogr.Open(
            os.path.join(str(tempdir), b'shapefile.shp'))

        for layer_num in xrange(shapefile.GetLayerCount()):
            layer = shapefile.GetLayer(layer_num)
            for feature_num in xrange(layer.GetFeatureCount()):
                feature = layer.GetFeature(feature_num)
                location_code = feature.GetField(
                    configuration.get(self.project, 'location_id_field')
                    .encode('utf8'))
                geometry = feature.GetGeometryRef().ExportToWkt()

                yield (location_code, geometry)

    def __existing_measurements(self, project, mtype, contractor):
        logger.debug("project: {} mtype {} contractor {}".format(project, mtype, contractor))
        return models.Measurement.objects.filter(
            scheduled__project=project,
            scheduled__measurement_type=mtype,
            scheduled__contractor=contractor).select_related(
            "scheduled", "scheduled__location")
