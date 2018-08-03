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
import shutil
import json

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
from django.db import connection
from django.http import Http404
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.shortcuts import render
from django.template import RequestContext
from django.template.loader import render_to_string
from django.utils.functional import cached_property
from django.utils.text import Truncator
from django.utils.translation import ugettext as _
from django.views.generic.base import TemplateView
from django.views.decorators.csrf import csrf_exempt
from django.views.static import serve

from lizard_map.matplotlib_settings import SCREEN_DPI
from lizard_map.views import AppView
from lizard_map.views import MAP_LOCATION as EXTENT_SESSION_KEY
from lizard_ui.layout import Action
from lizard_ui.views import UiView

from lizard_progress import configuration
from lizard_progress import crosssection_graph
from lizard_progress import forms
from lizard_progress import models
from lizard_progress.changerequests.models import Request
from lizard_progress.email_notifications.models import NotificationSubscription
from lizard_progress.email_notifications.models import NotificationType
from lizard_progress.models import Location
from lizard_progress.models import MeasurementTypeAllowed
from lizard_progress.models import Measurement
from lizard_progress.models import Project
from lizard_progress.models import ReviewProject
from lizard_progress.models import has_access
from lizard_progress.models import has_access_reviewproject
from lizard_progress.models import Activity
from lizard_progress.models import UploadLog
from lizard_progress.models import UserProfile
from lizard_progress.models import AvailableMeasurementType
from lizard_progress.util import directories
from lizard_progress.util import geo
from lizard_progress.util import workspaces
from lizard_progress.forms import NewReviewProjectForm
from lizard_progress.forms import UploadReviews

logger = logging.getLogger(__name__)


UiView  # Don't delete, it is imported by ``views/activity.py``


# Decorator serving to assure the request is a AJAX request
def ajax_request(view):
    def wrapper(request, *args, **kwargs):
        if request.is_ajax():
            return view(request, *args, **kwargs)
        else:
            raise PermissionDenied
    return wrapper


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
        "name": ("naam A-Z", ("name", False)),
        "namereversed": ("naam Z-A", ("name", True)),
        "changerequest": ("aanvragen", ("num_open_requests", True))
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
        order = request.GET.get('orderby', self.sortparams.keys()[0])

        self.orderby = self.sortparams[order][0]
        self.order = self.sortparams[order][1]

        self.orderchoices = {
            key: value[0] for key, value in self.sortparams.iteritems()
            if not value[0] == self.orderby
        }

        try:
            getattr(self, 'projects')
        except AttributeError:
            self.projects = self.generate_project_list()

        return super(ProjectsMixin, self).get(request, *args, **kwargs)

    def generate_project_list(self):
        """Returns a list of projects the current user has access to."""

        projecttable = [p for p in Project.objects.prefetch_related(
            'organization', 'project_type', 'activity_set__contractor', 'activity_set__measurement_type')
            .filter(is_archived=False) if has_access(project=p, userprofile=self.profile)]

        NAs = [p for p in projecttable if getattr(p, self.order[0]) == "N/A"]
        notNAs = [p for p in projecttable if p not in NAs]

        sortedprojects = sorted(notNAs, reverse=self.order[1],
                                key=lambda a: getattr(a, self.order[0]))

        # Append keyless elements if ASC, otherwise insert
        if self.order[1]:
            sortedprojects += NAs
        else:
            sortedprojects = NAs + sortedprojects

        projects = sortedprojects
        return projects

    @cached_property
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

        return [p for p in Project.objects.filter(is_archived=True) if has_access(self.request.user, p)]

    @cached_property
    def organization(self):
        """Return organization name of current user."""
        return self.profile and self.profile.organization.name

    def user_can_upload_to_project(self):
        if not self.project:
            return False
        return self.project.can_upload(self.request.user)

    @cached_property
    def user_has_uploader_role(self):
        return (
            self.profile and
            self.profile.has_role(models.UserRole.ROLE_UPLOADER))

    @cached_property
    def total_requests(self):
        from lizard_progress.changerequests.models import Request
        if self.user_has_manager_role():
            if 'tot_requests' not in self.request.session:
                self.request.session['tot_requests'] = Request.objects.filter(
                    request_status=Request.REQUEST_STATUS_OPEN,
                    activity__project__organization=self.profile.organization,
                    activity__project__is_archived=False
                ).count()
                return self.request.session['tot_requests']
        else:
            if 'tot_requests' not in self.request.session:
                self.request.session['tot_requests'] = Request.objects.filter(
                    request_status=Request.REQUEST_STATUS_OPEN,
                    activity__contractor=self.profile.organization,
                    activity__project__is_archived=False
                ).count()
                return self.request.session['tot_requests']

    def total_activity_requests(self, activity):
        from lizard_progress.changerequests.models import Request
        if self.user_is_manager():
            return Request.objects.filter(
                request_status=Request.REQUEST_STATUS_OPEN,
                activity__project__organization=self.profile.organization,
                activity=activity
            ).count()
        else:
            return Request.objects.filter(
                request_status=Request.REQUEST_STATUS_OPEN,
                activity__contractor=self.profile.organization,
                activity=activity
            ).count()

    @cached_property
    def activity_requests(self):
        # TODO: refactor this. Too many separate database queries.
        for activity in self.activities:
            yield activity, self.total_activity_requests(activity)

    @property
    def projects_requests(self):
        # Goal is the following query:
        # select distinct p.id as project, count(a.id) as num_requests, array_agg(m.name) as mtypes
        # from lizard_progress_project p
        # inner join lizard_progress_activity a on a.project_id = p.id
        # inner join changerequests_request r on r.activity_id =a.id
        # inner join lizard_progress_availablemeasurementtype m on m.id = a.measurement_type_id
        # group by p.id

        activities = Activity.objects.filter(project__in=self.projects)\
                                     .prefetch_related('measurement_type')

        avalues = activities.values('project', 'measurement_type')

        mtypes = AvailableMeasurementType.objects.filter(id__in=avalues.values_list('measurement_type_id', flat=True))

        mtvalues = mtypes.values('id', 'name')
        # probably still optimizable
        for project in self.projects:
            mtypes = [m['name'] for m in mtvalues if m['id'] in [_['measurement_type']
                                                                 for _ in avalues if _['project'] == project.id]]

            yield project, self.num_project_requests(project), mtypes

        # # before:
        # for project in self.projects:
        #    mtypes = project.activity_set.all()\
        #                                 .distinct('measurement_type')\
        #                                 .values_list('measurement_type__name', flat=True)
        #    yield project, self.num_project_requests(project), mtypes

    def num_project_requests(self, project):
        # TODO: refactor with database-level annotations/aggregations.
        # Way too many requests!
        if self.user_is_manager():
            return project.num_open_requests
        else:
            return project.num_open_requests_for_contractor(
                self.profile.organization)

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

    @property
    def measurementtypes(self):
        mtypes = list(MeasurementTypeAllowed.objects.select_related(
            'mtype').filter(
            organization=self.profile.organization
        ))
        user_mtypes = sorted(list(set([str(x.mtype) for x in
                                       mtypes])))
        return user_mtypes

    @property
    def is_simple(self):
        """A simplified project."""
        return self.project.is_simple

    @property
    def user_is_viewer(self):
        """A viewer is basically a contractor in a simple project, for which
        we want to show a simplified interface. The exception is if you're
        the contractor in your own project.
        """
        return (self.is_simple and
                self.project.organization != self.profile.organization)


class ReviewProjectMixin(object):
    """Helper functions for working with reviewprojects in views"""
    all_review_projects = None

    reviewproject_id = None
    reviewproject = None

    def dispatch(self, request, *args, **kwargs):

        self.all_review_projects = ReviewProject.objects.filter(
            organization=self.organization).defer('reviews', 'feature_collection_geojson')\
            | ReviewProject.objects.filter(
                contractor=self.organization).defer('reviews', 'feature_collection_geojson')

        self.reviewproject_id = kwargs.get('review_id')

        if self.reviewproject_id:
            try:
                self.reviewproject = ReviewProject.objects.get(
                    id=self.reviewproject_id)
            except ReviewProject.DoesNotExist:
                raise Http404()
            # Simplified, ReviewProject doesn't have Activities.
            # Instead each ReviewProject has one 'Beheerder' and one 'Reviewer'
            # Thus a ReviewProject cannot be split up in multiple parts to be
            # reviewed.
            if has_access_reviewproject(project=self.reviewproject,
                                        contractor=self.reviewproject.contractor,
                                        userprofile=self.profile):
                self.has_full_access = has_access_reviewproject(
                    project=self.reviewproject,
                    contractor=self.reviewproject.contractor,
                    userprofile=self.profile)
            else:
                raise PermissionDenied()
        else:
            self.reviewproject_id = None

        return super(
            ReviewProjectMixin, self).dispatch(request, *args, **kwargs)

    def reviews(self):
        pass

    def empty_reviews(self):
        pass

    def user_is_manager(self):
        """User is a manager if his organization owns this projects
        and user has the ROLE_MANAGER role."""
        return (self.user_has_manager_role() and
                (not self.reviewproject or
                 self.profile.organization == self.reviewproject.organization))

    def user_has_manager_role(self):
        return (
            self.profile and
            self.profile.has_role(models.UserRole.ROLE_MANAGER))

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
                    description=self.reviewproject.name,
                    name=self.reviewproject.name,
                    url='/'))

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
                url=(settings.STATIC_URL +
                     "lizard_progress/" +
                     "Gebruikershandleiding_Uploadserver_v4.pdf"))
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


class InlineMapViewNew(View):
    template_name = 'lizard_progress/map_inline_new.html'

    def get(self, request, *args, **kwargs):
        # import pdb; pdb.set_trace()
        return super(InlineMapViewNew, self).get(request, *args, **kwargs)

    def extent(self):
        rd_extent = self.get_rd_extent()
        logger.debug("InlineMapViewNew rd extent %s", rd_extent)
        wgs_extent = geo.rd_to_wgs84_extent(rd_extent)
        logger.debug("InlineMapViewNew new extent %s", wgs_extent)
        return json.dumps(wgs_extent)

    # TODO: remove
    available_layers = []

    def get_rd_extent(self, change_request=None, location_code=None):
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

    def locations_geojson(self):
        """A FeatureCollection of locations."""
        import geojson

        activities = Activity.objects.filter(project=self.project)\
            .filter(measurement_type__slug__in=['dwarsprofiel',
                                                'dwarsprofielen_inpeiling',
                                                'dwarsprofielen_uitpeiling',
                                                'ribx_reiniging_riool',
                                                'ribx_reiniging_kolken',
                                                'ribx_reiniging_inspectie_riool'])

        chreqs = Request.objects.filter(activity__in=activities).distinct()
        layers = {}

        with connection.cursor() as cursor:
            # Activities
            for a in activities:
                q = """select json_build_object(
                'type', 'Feature',
                'geometry', ST_AsGeoJSON(ST_Transform(l.the_geom, 4326))::json,
                'properties', json_build_object(
                'type', 'location',
                'id', l.id,
                'loc_id', l.id,
                'code', l.location_code,
                'activity', a.name,
                'contractor', o.name,
                'loc_type', l.location_type,
                'planned_date', l.planned_date,
                'complete', l.complete,
                'measured_date', l.measured_date,
                'work_impossible', l.work_impossible,
                'not_part_of_project', l.not_part_of_project,
                'new', l.new
                )) as features
                from public.lizard_progress_location l
                inner join lizard_progress_activity a on a.id = l.activity_id
                inner join lizard_progress_organization o on o.id = a.contractor_id
                where l.the_geom is not null and l.activity_id = {}""".format(str(a.id))

                cursor.execute(q)
                features = [json.loads(r[0]) for r in cursor.fetchall()]
                layers[a.name] = geojson.FeatureCollection(features)

            for cr in chreqs:
                q = """select json_build_object(
                'type', 'Feature',
                'geometry', ST_AsGeoJSON(ST_Transform(cr.the_geom, 4326))::json,
                'properties', json_build_object(
                'type', 'request',
                'id', cr.id,
                'req_id', cr.id,
                'req_type', cr.request_type,
                'loc_type', l.location_type,
                'loc_id', l.id,
                'loc_geom', ST_AsGeoJSON(ST_Transform(l.the_geom, 4326))::json,
                'code', cr.location_code,
                'motivation', cr.motivation,
                'status', cr.request_status
                )) as features
                from changerequests_request cr
                inner join lizard_progress_activity a on cr.activity_id = a.id
                inner join lizard_progress_location l on cr.location_code = l.location_code
                where cr.activity_id in ({0})
                and l.activity_id in ({0})"""\
                    .format(
                    ', '.join(map(str, activities.values_list('id', flat=True))))

                cursor.execute(q)
                features = [json.loads(r[0]) for r in cursor.fetchall()]

                # Add source/target location for 'move location' requests:
                q = """select json_build_object(
                'type', 'Feature',
                'geometry', ST_AsGeoJSON(ST_Transform(l.the_geom, 4326))::json,
                'properties', json_build_object(
                'type', 'request',
                'id', cr.id,
                'req_id', cr.id,
                'req_type', cr.request_type,
                'loc_type', l.location_type,
                'loc_id', l.id,
                'cr_geom', ST_AsGeoJSON(ST_Transform(cr.the_geom, 4326))::json,
                'code', cr.location_code,
                'motivation', cr.motivation,
                'status', cr.request_status
                )) as features
                from changerequests_request cr
                inner join lizard_progress_location l on cr.location_code = l.location_code
                where cr.activity_id in ({0})
                and l.activity_id in ({0})"""\
                    .format(
                    ', '.join(map(str, activities.values_list('id', flat=True))))

                cursor.execute(q)
                features2 = [json.loads(r[0]) for r in cursor.fetchall()]
                layers['Aanvragen'] = geojson.FeatureCollection(features + features2)

            # If called from a ChangeReq page (Toon op kaart - link),
            # then pass the change request info
            if 'change_request' in self.kwargs:
                q = """select json_build_object(
                'type', 'Feature',
                'geometry', ST_AsGeoJSON(ST_Transform(cr.the_geom, 4326))::json,
                'old_geometry', ST_AsGeoJSON(ST_Transform(lold.the_geom, 4326))::json,
                'properties', json_build_object(
                'type', 'request',
                'id', cr.id,
                'req_id', cr.id,
                'req_type', cr.request_type,
                'loc_type', lnew.location_type,
                'loc_id', lnew.id,
                'code', cr.location_code,
                'old_code', cr.old_location_code,
                'motivation', cr.motivation,
                'status', cr.request_status
                )) as features
                from changerequests_request cr
                inner join lizard_progress_activity a on cr.activity_id = a.id
                inner join lizard_progress_location lnew on cr.location_code = lnew.location_code
                left join lizard_progress_location lold on cr.old_location_code = lold.location_code
                where cr.id = {}"""\
                    .format(self.kwargs.get('change_request', -1))

                cursor.execute(q)
                features = [json.loads(r[0]) for r in cursor.fetchall()]
                layers['OoI'] = geojson.FeatureCollection(features)

        res = json.dumps(layers)
        return (res)


@login_required
@ajax_request
def get_closest_to(request, *args, **kwargs):
    """ When clicked on the map, searches for nearest neighbours (one of every type) within
    active overlays (=activities).

    When clicked on a location or a request, selects it and its relations within active overlays.

    Returns array of html for found objects + some service info for the leaflet popup.
    """
    locations = None
    response = {}
    html = []
    tab_titles = []
    obj_ids = []
    latlng = []
    locationIds, changeRequests = [], []

    lat = request.GET.get('lat', None)
    lng = request.GET.get('lng', None)
    objType = request.GET.get('objType', 'location')
    objId = request.GET.get('objId', None)
    radius = request.GET.get('radius', 50)
    overlays = request.GET.getlist('overlays[]', [])

    proj = Project.objects.get(slug=kwargs['project_slug'])

    # Unclickable items work-around
    ALWAYS_VICINITY = len(overlays) > 2 and False

    if not objId or ALWAYS_VICINITY:
        # Clicked on the basemap, search objects in the vicinity of the clicked point
        # considering active overlays
        # NN search is more efficiently carried out by postgis
        q = """SELECT DISTINCT ON (loc.location_type) loc.id FROM lizard_progress_location loc
        INNER JOIN lizard_progress_activity a ON a.id = loc.activity_id
        AND a.name IN ({3})
        AND (ST_Expand(loc.the_geom, {2}) &&
        ST_Transform(ST_GeomFromEWKT('SRID=4326;POINT({0} {1})'), 28992)::geometry)
        ORDER BY loc.location_type, ST_Distance(loc.the_geom,
        ST_Transform(ST_GeomFromEWKT('SRID=4326;POINT({0} {1})'), 28992)::geometry) ASC;"""\
            .format(lng,
                    lat,
                    radius,
                    ', '.join(map(lambda _: '\'' + str(_) + '\'', overlays)))

        with connection.cursor() as cursor:
            cursor.execute(q)
            locationIds = [l[0] for l in cursor.fetchall()]
            cursor.close()

    else:
        if objType == 'location':
            rootLocation = Location.objects.get(id=objId)
            locations = Location.objects.filter(location_code=rootLocation.location_code)\
                                        .filter(activity__name__in=overlays)
            locationIds = Location.objects.filter(location_code=rootLocation.location_code)\
                                          .filter(activity__name__in=overlays).values_list('id', flat=True)
        else:
            changeRequests = [Request.objects.get(id=objId)]
            locationIds = Location.objects.filter(activity=changeRequests[0].activity)\
                                          .filter(location_code=changeRequests[0].location_code)\
                                          .filter(activity__name__in=overlays)\
                                          .values_list('id', flat=True)
    # If nothing found, return empty response
    if not (locationIds or changeRequests):
        return HttpResponse(json.dumps(response), content_type="application/json")

    if locationIds:
        # Take the first from the query result and select all locations with the same location code
        # (i.e. select the location with all its activities).
        locations = Location.objects.filter(id__in=locationIds)

        g = locations[0].the_geom
        g.transform(4326)

        # If object is a pipe, point the popup to its middlepoint.
        if isinstance(g.coords[0], tuple):
            lng = (g.coords[0][0] + g.coords[1][0]) / 2
            lat = (g.coords[0][1] + g.coords[1][1]) / 2
        else:
            lng, lat = g.coords[0], g.coords[1]

        all_loc_activities = Activity.objects.filter(id__in=locations.values_list('activity_id'))

        # #############################
        # Create html for sewer objects
        # #############################
        for loc in [l for l in locations if l.location_type in ['pipe', 'manhole', 'drain']]:
            g = loc.the_geom
            g.transform(4326)

            # If object is a pipe, point the popup to its middlepoint.
            if isinstance(g.coords[0], tuple):
                lng = (g.coords[0][0] + g.coords[1][0]) / 2
                lat = (g.coords[0][1] + g.coords[1][1]) / 2
            else:
                lng, lat = g.coords[0], g.coords[1]

            latlng.append([lat, lng])
            html.append(render_to_string('lizard_progress/measurement_types/ribx_newmap.html',
                                         {'locations': [loc]}, context_instance=RequestContext(request)))
            tab_titles.append(loc.location_type + ' ' + loc.location_code + ' ' +
                              Truncator(loc.activity.name).chars(14))
            obj_ids.append(loc.id)

        # ########################################
        # Create html for crossection measurements
        # ########################################
        xsects = [l for l in locations if l.location_type in ['point']]

        for loc in xsects:
            g = loc.the_geom
            g.transform(4326)
            latlng.append([g.coords[1], g.coords[0]])

            multiple_projects_graph_url = None
            if loc.close_by_locations_of_same_organisation().count() > 1:
                organization = loc.activity.project.organization
                multiple_projects_graph_url = reverse(
                    'crosssection_graph', kwargs=dict(
                        organization_id=organization.id,
                        location_id=loc.id))
            lhtml = render_to_string('lizard_progress/measurement_types/metfile_newmap.html',
                                     {'image_graph_url': 'xsecimage?loc_id={}'.format(loc.id),
                                      'location': loc,
                                      'measurements': loc.measurement_set.all().count(),
                                      'title': loc.location_code + ' ' + loc.activity.name,
                                      'multiple_projects_graph_url': multiple_projects_graph_url})
            tab_titles.append(loc.location_type + ' ' + loc.location_code + ' ' +
                              Truncator(loc.activity.name).chars(14))
            obj_ids.append(loc.id)
            html.append(lhtml)
        # END crossection graph

    # ###############################
    # Create html for Change Requests
    # ###############################
    if not changeRequests:
        changeRequests = Request.objects.\
            filter(location_code__in=locations.values_list('location_code'))\
            .filter(activity__in=all_loc_activities)

    for cr in changeRequests:
        g = cr.the_geom
        g.transform(4326)
        latlng.append([g.coords[1], g.coords[0]])
        html.append(
            render_to_string(
                'changerequests/detail_popup.html',
                {'cr': cr},
                context_instance=RequestContext(
                    request,
                    {'user_is_manager': UserProfile.get_by_user(
                        request.user).is_manager_in(cr.project),
                     'user_is_contractor': UserProfile.get_by_user(
                         request.user).organization == cr.activity.contractor}
                )
            )
        )
        tab_titles.append('Aanvraag ' + cr.type_description + ' ' + cr.location_code)
        obj_ids.append(cr.id)

    response = {
        'html': html,
        'tab_titles': tab_titles,
        'objIds': obj_ids,
        'latlng': latlng
    }
    # return HttpResponse(json.dumps(response), content_type="application/json")
    return HttpResponse(json.dumps(response), content_type="application/json")


def xsecimage(request, *args, **kwargs):

    from . import crosssection_graph as xsgr

    loc = Location.objects.get(id=request.GET.get('loc_id'))
    if Measurement.objects.filter(location=loc):
        canvas = xsgr.graph(loc, Measurement.objects.filter(location=loc))
        response = HttpResponse(content_type='image/png')
        canvas.print_png(response)
    else:
        response = HttpResponse()

    return response


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

    @cached_property
    def total_activities(self):
        # import pdb;pdb.set_trace()
        return self.project.activity_set.count()

    @cached_property
    def num_open_requests(self):
        return self.project.num_open_requests

    @cached_property
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
                filenames = [self.clean_filename(measurement.rel_file_path)
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
    total = activity.num_locations

    # Measured profiles
    done = activity.num_complete_locations

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
        if self.user_is_manager():
            try:
                project = Project.objects.get(slug=project_slug)
                project.archive()
                msg = "Bericht van de server: project '{}' wordt gearchiveerd."
            except:
                msg = ("Er is een fout opgetreden. Project '{}' "
                       "wordt NIET gearchiveerd.")
            messages.success(self.request, msg.format(project))
        else:
            messages.warning(
                self.request, "Permission denied. Login as a project manager.")

    def activate(self, project_slug):
        project = Project.objects.get(slug=project_slug)
        project.activate()
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

        org_files_dir = directories.abs_organization_files_dir(
            self.profile.organization)
        abs_project_files_dir = directories.abs_project_files_dir(project)
        for filename in os.listdir(org_files_dir):
            shutil.copy(os.path.join(org_files_dir, filename),
                        os.path.join(abs_project_files_dir, filename))

        return HttpResponseRedirect(
            reverse('lizard_progress_dashboardview',
                    kwargs={'project_slug': project.slug}))

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
        print('activity', activity)

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


class ReviewProjectsOverview(KickOutMixin, ReviewProjectMixin, TemplateView):
    template_name = 'lizard_progress/reviewprojects_overview.html'


class ReviewProjectView(KickOutMixin, ReviewProjectMixin, TemplateView):
    template_name = 'lizard_progress/reviewproject.html'

    def get(self, request, *args, **kwargs):
        if not hasattr(self, 'upload_reviews_form'):
            self.upload_reviews_form = forms.UploadReviews()
        if not hasattr(self, 'upload_shapefiles_form'):
            self.upload_shapefiles_form = forms.UploadShapefiles()

        return super(ReviewProjectView, self).get(request, *args, **kwargs)

    @property
    def breadcrumbs(self):
        """Breadcrumbs for this page."""
        # TODO: Implement if we want to add breadcrumbs
        pass

    @csrf_exempt
    def post(self, request, *args, **kwargs):
        if not self.reviewproject.can_upload(self.user):
            raise PermissionDenied()

        if 'Upload reviews' in request.POST:
            # Upload new reviews:
            self.upload_reviews_form = UploadReviews(request.POST,
                                                     request.FILES)
            if not self.upload_reviews_form.is_valid():
                return self.get(request, *args, **kwargs)

            cleaned_json_file = self.upload_reviews_form.cleaned_data['reviews']
            self.reviewproject.set_reviews(cleaned_json_file)

        if 'Upload shapefiles' in request.POST:
            # Upload new shapefiles:
            self.upload_shapefiles_form = forms.UploadShapefiles(request.POST,
                                                                 request.FILES)
            if not self.upload_shapefiles_form.is_valid():
                return self.get(request, *args, **kwargs)

            self.reviewproject.shape_files = self.upload_shapefiles_form.cleaned_data['shape_files']
            self.reviewproject.save()

        return HttpResponseRedirect(request.path)


class DownloadReviewProjectReviewsView(KickOutMixin, ReviewProjectMixin,
                                       TemplateView):

    def get(self, request, *args, **kwargs):
        reviewproject = ReviewProject.objects.get(id=self.reviewproject_id)
        reviews = reviewproject.reviews
        response = HttpResponse(json.dumps(reviews, indent=2),
                                content_type="application/json")
        response['Content-Disposition'] = \
            'attachment; filename="{reviewproject}-reviews.json"'.format(
                reviewproject=reviewproject.name
            )
        return response


class DownloadReviewProjectShapefilesView(KickOutMixin, ReviewProjectMixin,
                                          TemplateView):

    def get(self, request, *args, **kwargs):
        reviewproject = ReviewProject.objects.get(id=self.reviewproject_id)
        path = reviewproject.shape_files.path
        filename = os.path.basename(path)

        if settings.DEBUG or not platform.system() == 'Linux' or "+" in \
                path:
            logger.debug(
                "With DEBUG off, we'd serve the programfile via webserver.")
            logger.debug(
                "Instead, we let Django serve {}.\n".format(path))
            return serve(request, directories.absolute(path), '/')

        response = HttpResponse()
        response['X-Sendfile'] = directories.absolute(path)  # Apache
        response['X-Accel-Redirect'] = os.path.join(
            '/protected', path)  # Nginx
        response['Content-Disposition'] = (
            'attachment; filename="{filename}"'.format(filename=filename))

        # Unset the Content-Type as to allow for the webserver
        # to determine it.
        response['Content-Type'] = ''

        return response


class NewReviewProjectView(KickOutMixin, ReviewProjectMixin, TemplateView):
    template_name = 'lizard_progress/new_reviewproject.html'

    @models.UserRole.check(models.UserRole.ROLE_MANAGER)
    def dispatch(self, request, *args, **kwargs):
        return super(NewReviewProjectView, self).dispatch(
            request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        if not hasattr(self, 'form'):
            self.form = forms.NewReviewProjectForm(
                organization=self.profile.organization)
        return super(NewReviewProjectView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.form = NewReviewProjectForm(request.POST, request.FILES)
        if not self.form.is_valid():
            return self.get(request, *args, **kwargs)

        try:
            # url = request.get_host()
            ribx_file = self.form.cleaned_data['ribx']
            filler_file = self.form.cleaned_data['filler_file']
            contractor = self.form.cleaned_data['contractor']
            project_review = models.ReviewProject.create_from_ribx(
                name=self.form.cleaned_data['name'],
                ribx_file=ribx_file,
                organization=self.organization,
                contractor=contractor,
                inspection_filler=filler_file,
                request=request
            )

        except:
            # If something goes wrong, don't save anything, revert all back
            # TODO: revert everyting
            raise

        return HttpResponseRedirect('/us/reviews/')


def multiproject_crosssection_graph(request, organization_id, location_id):
    """Show a graph with all Dwarsprofielen of this organization that are
    closer than 10m to this location.

    """
    organization = get_object_or_404(models.Organization, id=organization_id)
    if models.Organization.get_by_user(request.user) != organization:
        raise PermissionDenied()

    location = get_object_or_404(models.Location, id=location_id)

    canvas = crosssection_graph.locations_close_by_graph(
        organization, location)

    response = HttpResponse(content_type='image/png')
    canvas.print_png(response)
    return response
