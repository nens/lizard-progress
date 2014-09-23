# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.txt.
"""Views for the lizard-progress app. Includes:

MapView - can show projects as map layers
DashboardView - shows a project's dashboard, can show graphs and
                offers CSV files for download.
DashboardAreaView - a graph of the project's progress (hence "lizard-progress")
DashboardCsvView - a csv file view
protected_file_download - to download some uploaded files
"""

import csv
import json
import logging
import os
import platform
import shutil

import osgeo.ogr

from matplotlib import figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext as _
from django.views.static import serve
from django import http
from django.contrib import auth

from lizard_map.matplotlib_settings import SCREEN_DPI
from lizard_map.views import AppView
from lizard_ui.layout import Action
from lizard_ui.views import UiView

from lizard_progress.changerequests import models as cmodels
from lizard_progress import models
from lizard_progress.models import Hydrovak
from lizard_progress.models import Project
from lizard_progress.models import has_access
from lizard_progress.util import directories

from lizard_progress import configuration
from lizard_progress import forms

logger = logging.getLogger(__name__)


class NoSuchFieldException(Exception):
    pass


class ProjectsMixin(object):
    """Helper functions for working with projects in views"""
    project_slug = None
    project = None
    activity = None

    def dispatch(self, request, *args, **kwargs):
        self.request = request
        self.user = request.user
        self.profile = models.UserProfile.get_by_user(self.user)

        self.project_slug = kwargs.get('project_slug')
        if self.project_slug:
            self.project = get_object_or_404(Project, slug=self.project_slug)
            if has_access(request.user, self.project):
                self.has_full_access = all(
                    has_access(
                        request.user, self.project, activity.contractor)
                    for activity in self.project.activity_set.all())
            else:
                raise PermissionDenied()
        else:
            self.project = None

        return super(
            ProjectsMixin, self).dispatch(request, *args, **kwargs)

    def projects(self):
        """Returns a list of projects the current user has access to."""

        projects = []
        for project in Project.objects.filter(is_archived=False):
            if has_access(self.request.user, project):
                projects.append(project)
        return projects

    def projects_archived(self):
        """Returns a list of archived projects the current user has
        access to."""

        projects = []
        for project in Project.objects.filter(is_archived=True):
            if has_access(self.request.user, project):
                projects.append(project)
        return projects

    def organization(self):
        """Return organization name of current user."""
        return self.profile and self.profile.organization.name

    def contractor(self):
        """Return user-in-this-project's contractor object, if one
        exists."""
        profile = self.profile
        project = self.project

        if profile and project and profile.organization:
            try:
                return models.Contractor.objects.get(
                    project=project, organization=profile.organization)
            except models.Contractor.DoesNotExist:
                return None

    def user_can_upload_to_project(self):
        if not self.project:
            return False
        return self.project.can_upload(self.request.user)

    def user_is_uploader(self):
        """User is an upload if his organization is a contractor in
        this project and user has role ROLE_UPLOADER."""
        return (self.user_has_uploader_role() and
                (not self.project or models.Activity.objects.filter(
                    project=self.project,
                    contractor=self.profile.organization)
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

    def user_has_usermanager_role(self):
        return (
            self.profile and
            self.profile.has_role(models.UserRole.ROLE_ADMIN))

    def change_requests_menu_string(self):
        from lizard_progress.changerequests.models import Request

        n = len(Request.open_requests_for_profile(
                self.project, self.profile))

        if n == 0:
            return ""
        else:
            return " ({n})".format(n=n)

    def project_home_url(self):
        if not self.project_slug:
            return reverse('lizard_progress_projecten')

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
    """Checks that the current user is logged in and has an
    organization. Sets self.organization if this is true, otherwise
    kicks out the user. Most normal views in the Upload Server require
    an organization."""
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

        # Find the user icon, add a profile URL
        if self.request.user.is_authenticated():
            for action in actions:
                if action.icon == 'icon-user':
                    action.url = reverse(
                        "lizard_progress_single_user_management",
                        kwargs={'user_id': self.request.user.id})
                    break

        # Prepend organization icon
        actions[0:0] = [
            Action(
                icon='icon-briefcase',
                name=self.organization,
                description=(_("Your current organization")))
            ]

        # Prepend documentation icon
        actions[0:0] = [
            Action(
                icon='icon-question-sign',
                name="Handleiding",
                description=(_("Download the manual")),
                url=settings.STATIC_URL +
                "lizard_progress/Gebruikershandleiding_Uploadserver.pdf")
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
        """List of layers available to draw. Per contractor,
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
                            "project_slug": self.project.slug})
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

    def open_changerequests(self):
        return cmodels.Request.open_requests_for_profile(
            self.project, self.profile)

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


class DashboardView(ProjectsView):
    """Show the dashboard page. The page shows activities in this project,
    number of planned and uploaded measurements, links to pages for
    planning and for adding and removing contractors and measurement
    types, and progress graphs.

    """

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


class DashboardCsvView(ProjectsView):
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

    def get(self, request, project_slug, contractor_slug):
        """Returns a CSV file for this contractor and measurement
        type."""

        self.contractor_instance = models.Contractor.objects.get(
            project=self.project, slug=contractor_slug)

        # Setup HttpResponse and a CSV writer
        response = http.HttpResponse(content_type="text/csv")
        writer = csv.writer(response)

        filename = '%s_%s.csv' % (self.project.slug, self.contractor_instance)

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
                    project=self.project,
                    contractor=self.contractor_instance,
                    location=l).count()) == 0:
                continue

            # Row has the location's id first, then some information
            # per measurement type.
            row = [l.location_code]
            for mtype in measurement_types:
                try:
                    scheduled = ScheduledMeasurement.objects.get(
                        project=self.project,
                        contractor=self.contractor_instance,
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
def dashboard_graph(
        request, project_slug, activity_id):
    """Show the work in progress in pie charts.

    A single PNG image is returned as a response.
    """
    project = get_object_or_404(Project, slug=project_slug)
    activity = get_object_or_404(models.Activity, pk=activity_id)

    if (not has_access(request.user, project, activity.contractor)
            or activity.project != project):
        raise PermissionDenied()

    fig = ScreenFigure(500, 300)  # in pixels
    fig.text(
        0.5, 0.85,
        ('Uitgevoerde werkzaamheden {activity}'
         .format(activity=activity)),
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

    subplots = subplot_generator(1)

    # Profiles to be measured
    total = activity.num_locations()

    # Measured profiles
    done = activity.num_complete_locations()

    todo = total - done
    x = [done, todo]
    labels = ['Wel', 'Niet']
    colors = ['#50CD34', '#FE6535']
    ax = fig.add_subplot(subplots.next())
    ax.pie(x, labels=labels, colors=colors, autopct=autopct)
    ax.set_title(unicode(activity), y=y_title)
    ax.set_aspect('equal')  # circle

    # Create the response
    response = http.HttpResponse(content_type='image/png')
    canvas = FigureCanvas(fig)
    canvas.print_png(response)
    return response


@login_required
def protected_file_download(request, project_slug, activity_id,
                            filename):
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

    # XXXX
    project = get_object_or_404(models.Project, slug=project_slug)
    activity = get_object_or_404(models.Activity, pk=activity_id)

    if activity.project != project:
        return http.HttpResponseForbidden()

    logger.debug("Incoming programfile request for %s", filename)

    if '/' in filename or '\\' in filename:
        # Trickery?
        logger.warn("Returned Forbidden on suspect path %s" % (filename,))
        return http.HttpResponseForbidden()

    if not has_access(request.user, project, activity.contractor):
        logger.warn("Not allowed to access %s", filename)
        return http.HttpResponseForbidden()

    file_path = directories.make_uploaded_file_path(
        directories.BASE_DIR, activity, filename)
    nginx_path = directories.make_uploaded_file_path(
        '/protected', activity, filename)

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
        logger.debug(
            "Instead, we let Django serve {}.\n".format(file_path))
        return serve(request, file_path, '/')
    return response


class ArchiveProjectsOverview(ProjectsView):
    template_name = 'lizard_progress/archive.html'

    def archive_years(self):
        years = list(
            set([p.created_at.year for p in self.projects_archived()]))
        years.sort()
        years.reverse()
        return years

    def project_types(self):
        return models.ProjectType.objects.filter(
            organization=self.organization)

    def archive_tree(self):
        archive_tree = {}
        projects_archived = Project.objects.filter(
            id__in=[p.id for p in self.projects_archived()])

        for archive_year in self.archive_years():
            archive_tree.update({archive_year: {}})

        for archive_year in self.archive_years():

            for project_type in self.project_types():
                projects = projects_archived.filter(
                    **{'created_at__year': archive_year,
                       'project_type': project_type})
                if projects.exists():
                    archive_tree[archive_year].update(
                        {project_type.name: projects})
        return archive_tree


class ArchiveProjectsView(ProjectsView):

    template_name = 'lizard_progress/dashboard.html'

    def archive(self, project_slug):
        is_archived = False
        if self.user_is_manager():
            try:
                is_archived = True
                project = Project.objects.get(slug=project_slug)
                project.is_archived = is_archived
                project.save()
                msg = "Project '{}' is gearchiveerd."
            except:
                msg = ("Er is een fout opgetreden. Project '{}' " +
                       "is NIET gearchiveerd.")
            messages.success(self.request, msg.format(project))
        else:
            messages.warning(
                self.request, "Permission denied. Login as a project manager.")

    def activate(self, project_slug):
        project = Project.objects.get(slug=project_slug)
        project.is_archived = False
        project.save()
        messages.success(
            self.request, "Project '{}' is geactiveerd.".format(project))

    def get(self, request, project_slug, *args, **kwargs):
        action = request.GET.get('action', None)
        if action == "archive":
            self.archive(project_slug)
        elif action == "activate":
            self.activate(project_slug)

        return HttpResponseRedirect(
            reverse('lizard_progress_dashboardview', kwargs={
                    'project_slug': project_slug}))


class NewProjectView(ProjectsView):
    template_name = "lizard_progress/newproject.html"

    @models.UserRole.check(models.UserRole.ROLE_MANAGER)
    def dispatch(self, request, *args, **kwargs):
        return super(NewProjectView, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        if not hasattr(self, 'form'):
            self.form = forms.NewProjectForm(
                organization=self.profile.organization)
        return super(NewProjectView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.form = forms.NewProjectForm(
            request.POST,
            organization=self.profile.organization)
        if not self.form.is_valid():
            return self.get(request, *args, **kwargs)

        project_type = self.form.cleaned_data['ptype']

        project = models.Project(
            name=self.form.cleaned_data['name'],
            organization=self.organization,
            project_type=project_type)
        project.set_slug_and_save()

        for i in range(1, 1 + self.form.NUM_ACTIVITIES):
            activity = self.form.cleaned_data['activity' + str(i)]
            contractor = self.form.cleaned_data['contractor' + str(i)]
            mtype = self.form.cleaned_data['measurementtype' + str(i)]

            if None in (activity, contractor, mtype):
                continue

            models.Activity.objects.create(
                name=activity,
                project=project,
                measurement_type=mtype,
                contractor=contractor)

        org_files_dir = directories.organization_files_dir(
            self.profile.organization)
        project_files_dir = directories.project_files_dir(project)
        for filename in os.listdir(org_files_dir):
            shutil.copy(os.path.join(org_files_dir, filename),
                        os.path.join(project_files_dir, filename))

        return HttpResponseRedirect(
            reverse('lizard_progress_project_configuration_view',
                    kwargs={'project_slug': project.slug}))

    def grouped_form_fields(self):
        listed_fields = list(self.form)

        fields = [[listed_fields[0]], [listed_fields[1]]]

        for i in range(2, len(listed_fields), 3):
            fields.append(listed_fields[i:i+3])

        return fields


class PlanningView(ProjectsView):
    template_name = 'lizard_progress/planning.html'

    def dispatch(self, request, *args, **kwargs):
        project = models.Project.objects.get(slug=kwargs.get('project_slug'))

        mtypes = (
            project.organization.visible_available_measurement_types().filter(
                measurementtype__project=project))

        if request.method == 'GET':
            self.form = forms.MtypeShapefileForm(mtypes=mtypes)
        elif request.method == 'POST':
            self.form = forms.MtypeShapefileForm(
                request.POST, request.FILES, mtypes=mtypes)

        self.contractor_slug = kwargs.pop('contractor_slug', None)

        return super(PlanningView, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
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


class EditContractorsMeasurementTypes(ProjectsView):
    template_name = "lizard_progress/edit_contractors.html"
    active_menu = "dashboard"

    def current_contractors(self):
        return models.Contractor.objects.filter(
            project=self.project)

    def current_mtypes(self):
        return models.MeasurementType.objects.filter(
            project=self.project)

    def contractors_to_add(self):
        return models.Organization.objects.exclude(
            contractor__project=self.project)

    def measurementtypes_to_add(self):
        return self.organization.visible_available_measurement_types().exclude(
            measurementtype__project=self.project)

    def post(self, request, project_slug):
        if not self.user_is_manager():
            raise PermissionDenied()

        form = forms.AddContractorMeasurementTypeForm(request.POST)
        if not form.is_valid():
            # Can't happen...
            logger.debug("Form is not valid")
            raise http.Http404()

        if form.cleaned_data.get('contractor'):
            self._save_contractor(form)

        if form.cleaned_data.get('measurementtype'):
            self._save_measurementtype(form)

        if form.cleaned_data.get('remove_contractor'):
            self._remove_contractor(form)

        if form.cleaned_data.get('remove_mtype'):
            self._remove_mtype(form)

        return HttpResponseRedirect(
            reverse(
                'lizard_progress_edit_contractors',
                kwargs={'project_slug': self.project_slug}))

    def _save_contractor(self, form):
        try:
            organization = models.Organization.objects.get(
                pk=form.cleaned_data['contractor'])
        except models.Organization.DoesNotExist:
            logger.debug("Organization id '{}' does not exist."
                         .format(form.cleaned_data['contractor']))
            raise http.Http404()

        args = {
            'project': self.project,
            'organization': organization
            }

        if not models.Contractor.objects.filter(**args).exists():
            contractor = models.Contractor(**args)
            contractor.set_slug_and_save()

    def _save_measurementtype(self, form):
        try:
            available_measurement_type = (
                models.AvailableMeasurementType.objects.get(
                    pk=form.cleaned_data['measurementtype']))
        except models.AvailableMeasurementType.DoesNotExist:
            logger.debug("Available mtype id '{}' does not exist."
                         .format(form.cleaned_data['measurementtype']))
            raise http.Http404()

        models.MeasurementType.objects.get_or_create(
            project=self.project,
            mtype=available_measurement_type,
            defaults={
                'icon_missing':
                available_measurement_type.default_icon_missing,
                'icon_complete':
                available_measurement_type.default_icon_complete
                })

    def _remove_contractor(self, form):
        try:
            contractor = models.Contractor.objects.get(
                pk=form.cleaned_data['remove_contractor'])
        except models.Contractor.DoesNotExist:
            raise http.Http404()

        if not contractor.has_measurements():
            contractor.delete()

    def _remove_mtype(self, form):
        try:
            mtype = models.MeasurementType.objects.get(
                pk=form.cleaned_data['remove_mtype'])
        except models.MeasurementType.DoesNotExist:
            raise http.Http404()

        if not mtype.has_measurements():
            mtype.delete()
