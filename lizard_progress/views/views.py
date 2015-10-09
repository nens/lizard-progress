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
import logging
import os
import platform
import shutil

from matplotlib import figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas

from django import http
from django.conf import settings
from django.contrib import auth
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.http import Http404
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils.functional import cached_property
from django.utils.translation import ugettext as _
from django.views.generic.base import TemplateView
from django.views.static import serve

from lizard_map.matplotlib_settings import SCREEN_DPI
from lizard_map.views import AppView
from lizard_map.views import MAP_LOCATION as EXTENT_SESSION_KEY
from lizard_ui.layout import Action
from lizard_ui.views import UiView

from lizard_progress import configuration
from lizard_progress import models
from lizard_progress.models import Location
from lizard_progress.models import Project
from lizard_progress.models import has_access
from lizard_progress.util import directories
from lizard_progress.util import workspaces
from lizard_progress.util import geo
from lizard_progress import crosssection_graph
from lizard_progress import forms
from lizard_progress.email_notifications.models import NotificationType
from lizard_progress.email_notifications.models import NotificationSubscription
from lizard_progress.changerequests.models import Request

logger = logging.getLogger(__name__)


class ProjectsMixin(object):
    """Helper functions for working with projects in views"""
    project_slug = None
    project = None
    activity = None
    sortparams = {
        "mostrecent": ("meest recent", ("created_at", True)),
        "leastrecent": ("minst recent", ("created_at", False)),
        "mosturgent": ("meest gereed", ("percentage_done", True)),
        "leasturgent": ("minst gereed", ("percentage_done", False)),
        "name": ("naam", ("name", False)),
        "namereversed": ("naam omgekeerd", ("name", True))
    }

    def dispatch(self, request, *args, **kwargs):
        self.project_slug = kwargs.get('project_slug')
        if self.project_slug:
            try:
                self.project = Project.objects.select_related(
                    'organization').prefetch_related('activity_set').get(
                    slug=self.project_slug)
            except Project.DoesNotExist:
                raise Http404()

            if has_access(project=self.project, userprofile=self.profile):
                self.has_full_access = all(
                    has_access(
                        project=self.project,
                        contractor=activity.contractor,
                        userprofile=self.profile)
                    for activity in self.project.activity_set.all())
            else:
                raise PermissionDenied()
        else:
            self.project = None

        return super(
            ProjectsMixin, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        order = request.GET.get('orderby')
        try:
            self.orderby = self.sortparams[order][0]
        except KeyError:
            order = "mostrecent"
            self.orderby = self.sortparams[order][0]
        self.order = self.sortparams[order][1]
        self.orderchoices = {
            key: value[0] for key, value in self.sortparams.iteritems()
            if not value[0] == self.orderby
            }
        return super(ProjectsMixin, self).get(request, *args, **kwargs)

    def projects(self):
        """Returns a list of projects the current user has access to."""
        projecttable = Project.objects.select_related(
            'organization').prefetch_related(
            'activity_set__contractor').filter(is_archived=False)
        NAs = []
        notNAs = []
        for project in projecttable:
            if getattr(project, self.order[0]) == "N/A":
                NAs.append(project)
            else:
                notNAs.append(project)
        sortedprojects = sorted(notNAs, reverse=self.order[1],
               key=lambda a: getattr(a, self.order[0]))
        if self.order[1]:
            sortedprojects += NAs
        else:
            sortedprojects = NAs + sortedprojects
        projects = []
        for project in sortedprojects:
            if has_access(project=project, userprofile=self.profile):
                projects.append(project)
        return projects

    def activities(self):
        """If there is a current project, generate the activities inside
        it that this user has access to."""
        if not self.project:
            return

        for activity in self.project.activity_set.all():
            if has_access(
                    project=self.project,
                    contractor=activity.contractor,
                    userprofile=self.profile):
                yield activity

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
    kicks out the user. Most normal views in the Uploadservice require
    an organization."""
    def dispatch(self, request, *args, **kwargs):
        """You can only get here if you are part of some organization.
        So admin can't."""
        self.request = request
        self.user = request.user
        self.profile = models.UserProfile.get_by_user(self.user)

        self.organization = getattr(self.profile, 'organization', None)

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
                "lizard_progress/Gebruikershandleiding_Uploadserver_v4.pdf")
        ]

        return actions


class ProjectsView(KickOutMixin, ProjectsMixin, TemplateView):
    """Displays a list of projects to choose from."""
    template_name = "lizard_progress/projects.html"


class View(KickOutMixin, ProjectsMixin, TemplateView):
    """The app's root, shows a choice of projects, or a choice of
    dashboard / upload / map layer pages if a project is chosen."""

    template_name = 'lizard_progress/home.html'


class InlineMapView(View):
    template_name = 'lizard_progress/map_inline.html'


class MapView(View, AppView):
    """View that can show a project's locations as map layers."""
    template_name = 'lizard_progress/map.html'

    def get(self, request, *args, **kwargs):
        """Besides rendering the map page, zoom to the extent of all our
        layers, and place them in the workspace."""

        # XXX Note that this is somewhat dubious as some JS functionality
        # (like toggling the visibility of the workspace items) also calls
        # *this entire view* to update its view of the workspace items.
        workspaces.set_items(request, self.available_layers)
        self.set_extent(request.session,
                        change_request=kwargs.get('change_request', None),
                        location_code=kwargs.get('location_code', None))
        return super(MapView, self).get(request, *args, **kwargs)

    @cached_property
    def available_layers(self):
        """List of layers available to draw. One layer per activity. These
        are lizard_progress.util.workspaces.MapLayer instances."""

        # Return a tuple instead of a list because an immutable value
        # is safer with @cached_property.
        return tuple(self.project.available_layers(self.request.user))

    def set_extent(self, session, change_request, location_code):
        """We need min-x, max-x, min-y and max-y as Google coordinates."""
        rd_extent = self.get_rd_extent(change_request, location_code)

        if rd_extent:
            formatted_google_extent = geo.rd_to_google_extent(rd_extent)
            session[EXTENT_SESSION_KEY] = formatted_google_extent

    def get_rd_extent(self, change_request, location_code):
        """Compute the extent we want to zoom to, in RD."""

        locations = Location.objects.filter(activity__project=self.project)
        if location_code:
            locations = locations.filter(location_code=location_code)

        # Layers MAY define their own extent (used for the extents of
        # change requests). Otherwise layer.extent will be None.
        extra_extents = [layer.extent for layer in self.available_layers
                         if layer.extent is not None]

        if change_request:
            extent = Request.objects.get(id=change_request).map_layer().extent
        elif locations.exists():
            # Start with this extent, add the extras to this
            extent = locations.extent()
        elif extra_extents:
            # No locations, but extra extents: use the first as start extent
            extent = extra_extents.pop()
        else:
            # There is nothing to zoom to...
            return None

        minx, miny, maxx, maxy = extent

        # Combine extra extents
        for extra_extent in extra_extents:
            e_minx, e_miny, e_maxx, e_maxy = extra_extent
            minx = min(minx, e_minx)
            miny = min(miny, e_miny)
            maxx = max(maxx, e_maxx)
            maxy = max(maxy, e_maxy)

        return (minx, miny, maxx, maxy)

    @property
    def content_actions(self):
        """Hide everything but the zoom to start location action"""
        return [action for action in
                super(MapView, self).content_actions
                if 'load-default-location' in action.klass]

    @property
    def sidebar_actions(self):
        """..."""
        actions = super(MapView, self).sidebar_actions
        actions[0].name = 'Kaartlagen'
        return actions       

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
    def total_activities(self):
        return self.project.activity_set.count()

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


class ActivitiesView(ProjectsView):
    """Show the activities page. The page shows activities in this project,
    number of planned and uploaded measurements, links to pages for
    planning and for adding and removing contractors and measurement
    types, and progress graphs.

    """

    template_name = 'lizard_progress/activities.html'
    active_menu = "dashboard"

    @property
    def breadcrumbs(self):
        """Breadcrumbs for this page."""

        crumbs = super(DashboardView, self).breadcrumbs

        crumbs.append(
            Action(
                name="Activities",
                description=("{project} dashboard"
                             .format(project=self.project.name)),
                url=reverse(
                    'lizard_progress_activitiesview',
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

    def get(self, request, project_slug, activity_id):
        """Returns a CSV file for this activity."""

        self.activity = models.Activity.objects.get(pk=activity_id)

        # Setup HttpResponse and a CSV writer
        response = http.HttpResponse(content_type="text/csv")
        writer = csv.writer(response)

        filename = '%s_%s.csv' % (self.activity.project.slug, activity_id)

        response['Content-Disposition'] = ('attachment; filename=%s' %
                                           (filename,))

        locations = self.activity.location_set.all()

        # Write header row
        writer.writerow(['Locatie ID', 'Geupload in'])

        # Write rest of the rows
        for location in locations:
            # Row has the location's id first, then some information
            # per measurement type.
            row = [location.location_code]
            if location.complete:
                # Nice sorted list of filenames and dates.
                filenames = [self.clean_filename(measurement.filename)
                             for measurement in
                             location.measurement_set.all()]

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

    if (not has_access(request.user, project, activity.contractor) or
            activity.project != project):
        raise PermissionDenied()

    fig = ScreenFigure(500, 300)  # in pixels
    fig.text(
        0.5, 0.95,
        'Uitgevoerd {activity}'.format(activity=activity),
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
def measurement_download_or_delete(
        request, project_slug, activity_id, measurement_id, filename):
    project = get_object_or_404(models.Project, slug=project_slug)
    activity = get_object_or_404(models.Activity, pk=activity_id)
    measurement = get_object_or_404(
        models.Measurement, pk=measurement_id, location__activity=activity)

    if activity.project != project:
        return http.HttpResponseForbidden()
    if filename != measurement.base_filename:
        raise Http404()

    logger.debug("Incoming programfile request for %s", filename)

    if not has_access(request.user, project, activity.contractor):
        logger.warn("Not allowed to access %s", filename)
        return http.HttpResponseForbidden()

    if request.method == 'GET':
        return protected_file_download(request, activity, measurement)

    if request.method == 'DELETE':
        return delete_measurement(request, activity, measurement)

    # This gives a somewhat documented 405 error
    return http.HttpResponseNotAllowed(('GET', 'DELETE'))


def protected_file_download(request, activity, measurement):
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

    nginx_path = directories.make_nginx_file_path(
        activity, measurement.filename)

    # This is where the magic takes place.
    response = http.HttpResponse()
    response['X-Sendfile'] = measurement.filename  # Apache
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
            "Instead, we let Django serve {}.\n".format(measurement.filename))
        return serve(request, measurement.filename, '/')
    return response


def delete_measurement(request, activity, measurement):
    """Delete the measurement. This undos everything releted to this
    particular measurement. If the uploaded file contained several
    measurements, the others are unaffected and the uploaded file is
    still there.
    """
    # We need write access in this project.
    if not models.has_write_access(
            request.user,
            project=activity.project,
            contractor=activity.contractor):
        http.HttpResponseForbidden()

    # Actually delete it.
    measurement.delete(
        notify=True,
        deleted_by_contractor=activity.contractor.contains_user(request.user))

    # Just return success -- this view is called from Javascript.
    return http.HttpResponse()


class ArchiveProjectsOverview(ProjectsView):
    template_name = 'lizard_progress/archive.html'

    def archive_years(self):
        years = list(
            set([p.created_at.year for p in self.projects_archived()]))
        years.sort(reverse=True)
        return years

    def project_types(self):
        return models.ProjectType.objects.filter(
            organization=self.organization)

    def archive_tree(self):
        archive_tree = {}
        projects_archived = Project.objects.filter(
            id__in=[p.id for p in self.projects_archived()])

        for archive_year in self.archive_years():
            archive_tree.update({archive_year: []})

        for archive_year in self.archive_years():

            for project_type in self.project_types():
                projects = projects_archived.filter(
                    created_at__year=archive_year,
                    project_type=project_type)
                if projects.exists():
                    archive_tree[archive_year].append(
                        (project_type.name, projects))
            projects_no_type = projects_archived.filter(
                created_at__year=archive_year,
                project_type__isnull=True)
            if projects_no_type.exists():
                archive_tree[archive_year].append((
                    _("Projects without project type"), projects_no_type))

        # Don't return dicts, hard to sort them
        return sorted(archive_tree.items())


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
    template_name = "lizard_progress/new_project.html"

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

            if None in (contractor, mtype):
                continue

            activity = models.Activity.get_unique_activity_name(
                project, contractor, mtype, activity)

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
            reverse('lizard_progress_dashboardview',
                    kwargs={'project_slug': project.slug}))

        return activity

    def grouped_form_fields(self):
        listed_fields = list(self.form)

        fields = [[listed_fields[0]], [listed_fields[1]]]

        for i in range(2, len(listed_fields), 3):
            fields.append(listed_fields[i:i + 3])

        return fields


class EditActivities(ProjectsView):
    template_name = "lizard_progress/edit_activities.html"
    active_menu = "dashboard"

    def url(self):
        return reverse(
            'lizard_progress_edit_activities', kwargs=dict(
                project_slug=self.project.slug))

    def contractors_to_add(self):
        return list(models.Organization.objects.all())

    def measurement_types_to_add(self):
        return list(
            self.project.organization.visible_available_measurement_types())

    def current_activities(self):
        return list(self.project.activity_set.all())

    def get(self, request, project_slug):
        if not hasattr(self, 'form'):
            self.form = forms.AddActivityForm(None, self.project)

        return super(EditActivities, self).get(request, project_slug)

    def post(self, request, project_slug):
        if not self.user_is_manager():
            raise PermissionDenied()

        self.form = forms.AddActivityForm(request.POST, self.project)

        if not self.form.is_valid():
            return self.get(request, project_slug)

        self._add_activity(self.form)

        return HttpResponseRedirect(self.url())

    def _add_activity(self, form):
        name = models.Activity.get_unique_activity_name(
            self.project, form.cleaned_data['contractor'],
            form.cleaned_data['measurementtype'],
            form.cleaned_data['description'])
        models.Activity.objects.create(
            project=self.project,
            contractor=form.cleaned_data['contractor'],
            measurement_type=form.cleaned_data['measurementtype'],
            name=name)


class DeleteActivity(ProjectsView):
    def post(self, request, project_slug, activity_id):
        if not self.user_is_manager():
            raise PermissionDenied()

        activity = get_object_or_404(models.Activity, pk=activity_id)

        if activity.project.slug != project_slug:
            raise PermissionDenied()

        if activity.has_measurements():
            raise PermissionDenied()

        activity.delete()

        return HttpResponseRedirect(reverse(
            'lizard_progress_edit_activities', kwargs=dict(
                project_slug=self.project.slug)))


class ConfigurationView(ProjectsView):
    template_name = 'lizard_progress/project_configuration_page.html'
    active_menu = "project_config"

    def config_options(self):
        config = configuration.Configuration(project=self.project)
        return list(config.options())

    def post(self, request, *args, **kwargs):
        redirect = HttpResponseRedirect(reverse(
            "lizard_progress_project_configuration_view",
            kwargs={'project_slug': self.project_slug}))

        if not self.project.is_manager(self.user):
            return redirect

        for key in configuration.CONFIG_OPTIONS:
            option = configuration.CONFIG_OPTIONS[key]
            value_str = request.POST.get(key, '')
            try:
                value = option.translate(value_str)
                # No error, set it
                config = configuration.Configuration(project=self.project)
                config.set(option, value)
            except ValueError:
                pass

        return redirect


class EmailNotificationConfigurationView(ProjectsView):
    template_name = 'lizard_progress/project_email_config_page.html'
    active_menu = 'project_email_config'

    def config_options(self):
        project_content_type = ContentType.objects.get_for_model(self.project)
        current_subscriptions = NotificationSubscription.objects.filter(
            subscriber_content_type=project_content_type,
            subscriber_object_id=self.project.id)
        all_notification_types = NotificationType.objects.all()
        return [
            (notification_type, current_subscriptions.filter(
                notification_type=notification_type).exists())
            for notification_type in all_notification_types
        ]

    def post(self, request, *args, **kwargs):
        redirect = HttpResponseRedirect(reverse(
            "lizard_progress_project_email_config_view",
            kwargs={'project_slug': self.project_slug}))

        if not self.project.is_manager(self.user):
            return redirect

        for option, old_value in self.config_options():
            new_value = request.POST.get(option.name, '')
            if not old_value and new_value:
                option.subscribe(self.project)
            elif old_value and not new_value:
                option.unsubscribe(self.project)

        return redirect


def multiproject_crosssection_graph(request, organization_id, location_code):
    """Show a graph with all Dwarsprofielen of this code that have been
    uploaded in this organization.

    """
    organization = get_object_or_404(models.Organization, id=organization_id)
    if models.Organization.get_by_user(request.user) != organization:
        raise PermissionDenied()

    canvas = crosssection_graph.location_code_graph(
        organization, location_code)

    response = HttpResponse(content_type='image/png')
    canvas.print_png(response)
    return response
