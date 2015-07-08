# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

# Python 3 is coming
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import datetime
import functools
import json
import logging
import os
import random
import shutil
import string

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.gis.db import models
from django.contrib.gis.geos import LineString
from django.contrib.gis.geos import MultiLineString
from django.contrib.gis.geos import fromstr
from django.contrib.gis.gdal import DataSource
from django.contrib.sites.models import Site
from django.core.exceptions import PermissionDenied
from django.db.models.signals import post_save
from django.core.urlresolvers import reverse
from django.db import connection
from django.dispatch import receiver
from django.http import HttpRequest
from django.template.defaultfilters import slugify
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

from jsonfield import JSONField

import lizard_progress.specifics
from lizard_progress.email_notifications import notify
from lizard_progress.email_notifications.models import NotificationType
from lizard_progress.email_notifications.models import NotificationSubscription
from lizard_progress.util import directories

RDNEW = 28992
SRID = RDNEW

logger = logging.getLogger(__name__)


class AlreadyUploadedError(ValueError):
    def __init__(self, filename):
        self.filename = filename
        super(AlreadyUploadedError, self).__init__(
            "{} was already uploaded.".format(filename))


def is_line(geom):
    """Decide whether geom is a line geometry (of several possible types)."""
    if isinstance(geom, LineString):
        # django.contrib.gis.geos.LineString
        return True

    if hasattr(geom, 'ExportToWkt') and 'LINESTRING' in geom.ExportToWkt():
        # osgeo.ogr.Geometry linestring
        return True

    if isinstance(geom, basestring) and 'LINESTRING' in geom:
        # A WKT string
        return True

    return False


def osgeo_3d_line_to_2d_wkt(geom):
    points = geom.GetPoints()
    return 'LINESTRING({} {}, {} {})'.format(
        points[0][0], points[0][1],
        points[1][0], points[1][1])


def osgeo_3d_point_to_2d_wkt(geom):
    point = geom.GetPoint()
    return 'POINT({} {})'.format(point[0], point[1])


class ErrorMessage(models.Model):
    error_code = models.CharField(max_length=30)
    error_message = models.CharField(max_length=300)

    def __unicode__(self):
        return self.error_code

    def format(self, *args, **kwargs):
        return self.error_message.format(*args, **kwargs)

    @classmethod
    def format_code(cls, error_code, *args, **kwargs):
        try:
            error_message = cls.objects.get(error_code=error_code)
        except cls.DoesNotExist:
            return (
                "UNKNOWNCODE",
                "Could not get error code {0} from database".format(error_code)
            )

        return error_code, error_message.format(*args, **kwargs)


class Organization(models.Model):
    name = models.CharField(max_length=128)
    description = models.CharField(max_length=256, blank=True, null=True)
    errors = models.ManyToManyField(ErrorMessage)

    # Only is_project_owner organizations are allowed to give the project
    # manager role to their users
    is_project_owner = models.BooleanField(default=False)

    lizard_config = models.ForeignKey(
        'LizardConfiguration', blank=True, null=True)

    mtypes_allowed = models.ManyToManyField(
        'AvailableMeasurementType',
        through='MeasurementTypeAllowed')

    class Meta:
        ordering = ('name',)

    @classmethod
    def users_in_same_organization(cls, user):
        """Returns a list of user in same organization."""
        organization = UserProfile.objects.get(user=user).organization
        return User.objects.filter(userprofile__organization=organization)

    @property
    def users(self):
        return User.objects.filter(userprofile__organization=self)

    @property
    def slug(self):
        """For use in filenames, etc."""
        slug = self.name.lower()
        # Remove 'bad' characters
        for c in "()\"'/\\&.#%{}<>*?$!:@+`|=":
            slug = slug.replace(c, '')

        # Turn whitespace into '_'
        slug = '_'.join(slug.split())
        return slug

    @classmethod
    def get_by_user(cls, user):
        user_profile = UserProfile.get_by_user(user)
        if user_profile is not None:
            return user_profile.organization
        return None

    def allowed_available_measurement_types(self):
        return self.mtypes_allowed.all()

    def visible_available_measurement_types(self):
        """Return only those allowed types that the organization wants
        to see."""
        return self.allowed_available_measurement_types().filter(
            measurementtypeallowed__visible=True)

    def contains_user(self, user):
        """Returns true if user is in this organization."""
        user_profile = UserProfile.get_by_user(user)
        return user_profile is not None and user_profile.organization == self

    def __unicode__(self):
        return self.name

    def set_error_codes(self, codes):
        for code in codes:
            error = ErrorMessage.objects.get(error_code=code)
            self.errors.add(error)


class ProjectType(models.Model):
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True, null=True)
    organization = models.ForeignKey(Organization)
    default = models.BooleanField(
        help_text="The type wil be applied to projects by default",
        default=False)

    class Meta:
        unique_together = (('name', 'organization'),)

    def __unicode__(self):
        return unicode(self.name)


class UserRole(models.Model):
    # Can make new projects, configure running projects
    ROLE_MANAGER = "manager"
    # This role is commented out because right now I *think* we can keep this
    # implicit -- all members of an organization are viewers.
    # ROLE_VIEWER = "viewer"
    # Can upload measurements and reports if user's organization is a
    # contractor in the project
    ROLE_UPLOADER = "uploader"
    # Can assign roles to people in the organization, create and delete user
    # accounts belonging to this organization.
    ROLE_ADMIN = "admin"

    # Rows according to those roles are entered into the database by
    # means of a fixture.
    code = models.CharField(max_length=10)
    description = models.CharField(max_length=100)

    def __unicode__(self):
        return self.description

    @classmethod
    def all_role_codes(cls):
        return (cls.ROLE_MANAGER, cls.ROLE_UPLOADER, cls.ROLE_ADMIN)

    @classmethod
    def check(cls, role):
        """Return a view decorator that checks if the logged in user
        has a given role, otherwise raises PermissionDenied."""

        def view_wrapper(view):
            """Decorator. Returns a wrapped version of the view that
            checks roles."""

            @functools.wraps(view)
            def wrapped(*args, **kwargs):
                # The first or second argument must be the request
                if isinstance(args[0], HttpRequest):
                    request = args[0]
                else:
                    request = args[1]

                profile = UserProfile.get_by_user(request.user)
                if not profile or not profile.has_role(role):
                    raise PermissionDenied()

                return view(*args, **kwargs)
            return wrapped
        return view_wrapper


class UserProfile(models.Model):
    user = models.ForeignKey(User, unique=True)
    organization = models.ForeignKey(Organization)
    roles = models.ManyToManyField(UserRole)

    @classmethod
    def get_by_user(cls, user):
        if not user or not user.is_authenticated():
            return None
        try:
            return cls.objects.select_related(
                'organization', 'user').prefetch_related(
                'roles').get(user=user)
        except cls.DoesNotExist:
            return None

    def __unicode__(self):
        return "{0} {1}".format(self.user.username,
                                self.organization.name)

    def has_role(self, role_code):
        # Cache them, this is used all over the place.
        # This change plus the prefetch_related in get_by_user
        # made a random page go from 249 queries to 15!!
        if not hasattr(self, '_roles'):
            self._roles = set(role.code for role in self.roles.all())

        return role_code in self._roles

    def is_manager_in(self, project):
        return self.has_role(UserRole.ROLE_MANAGER) and (
            project.organization == self.organization)

    def roles_description(self):
        return ", ".join(
            UserRole.objects.get(code=code).description
            for code in UserRole.all_role_codes()
            if self.has_role(code))


def has_access(user=None, project=None, contractor=None, userprofile=None):
    """Test whether user has access to this project (showing data of
    this contractor organization)."""

    if userprofile is None:
        userprofile = UserProfile.get_by_user(user)

    if userprofile is None:
        return False

    if project.is_archived:
        # Only organization's project managers have access
        return (userprofile.organization ==
                project.organization) and (
            userprofile.has_role(UserRole.ROLE_MANAGER))

    if (userprofile.organization == project.organization):
        # Everybody in the project's organization can see it.
        return True

    # A user may only see projects of other organizations if this user
    # is an Uploader.
    if not userprofile.has_role(UserRole.ROLE_UPLOADER):
        return False

    if contractor:
        # If it is about one contractor's data in this project,
        # it's only visible for that contractor.
        return contractor == userprofile.organization
    else:
        # If this is not about some specific contractor's data,
        # all contractors also have access.
        for activity in project.activity_set.all():
            if activity.contractor == userprofile.organization:
                return True

    return False


def has_write_access(
        user=None, project=None, contractor=None, userprofile=None):
    """Test whether user has write access to this project (editing data of
    this contractor organization)."""

    if userprofile is None:
        userprofile = UserProfile.get_by_user(user)

    if userprofile is None:
        return False

    # Either be a manager in this project's organization, or
    # an uploader in the other (if it isn't archived).
    if (userprofile.organization == project.organization) and (
            userprofile.has_role(UserRole.ROLE_MANAGER)):
        return True

    if project.is_archived:
        return False

    # Otherwise the data is only editable if contractor is not None (the
    # data is from some uploading organization) and the user is Uploader
    # in it.
    return (
        contractor and userprofile.has_role(UserRole.ROLE_UPLOADER) and
        contractor == userprofile.organization)


def all_measurements(project, organization):
    """Return an iterable of all measurements taken for this
    project and contractor."""

    return Measurement.objects.filter(
        location__activity__project=project,
        location__activity__contractor=organization)


def current_files(measurements):
    """Given an iterable of measurements, return a set of all
    filenames used to create them.

    One file can contain many measurements, so if we didn't use a set
    we could end up with many duplicates."""

    return set(measurement.filename for measurement in measurements)


class Project(models.Model):
    name = models.CharField(max_length=50, unique=False,
                            verbose_name='projectnaam')
    slug = models.SlugField(max_length=60, unique=True)
    organization = models.ForeignKey(Organization, null=False)
    is_archived = models.BooleanField(default=False)

    project_type = models.ForeignKey(ProjectType, null=True, blank=True)
    created_at = models.DateTimeField(default=datetime.datetime.now)

    class Meta:
        ordering = ('name',)
        unique_together = [('name', 'organization')]

    def __unicode__(self):
        return unicode(self.name)

    def get_absolute_url(self):
        return reverse('lizard_progress_dashboardview',
                       kwargs={'project_slug': self.slug, })

    def is_manager(self, user):
        profile = UserProfile.get_by_user(user)
        return (self.organization == profile.organization and
                profile.has_role(UserRole.ROLE_MANAGER))

    def set_slug_and_save(self):
        """Call on an unsaved project.

        Sets a random slug, saves the project, then sets a new slug
        based on primary key and name."""
        chars = list(string.lowercase)
        random.shuffle(chars)
        self.slug = ''.join(chars)
        self.save()

        self.slug = "{id}-{slug}".format(
            id=self.id,
            slug=slugify(self.name))
        self.save()

    def specifics(self, activity=None):
        return lizard_progress.specifics.Specifics(self, activity)

    def number_of_locations(self):
        return Location.objects.filter(
            activity__project=self,
            not_part_of_project=False).count()

    def number_of_complete_locations(self):
        return Location.objects.filter(
            activity__project=self, complete=True,
            not_part_of_project=False).count()

    def percentage_done(self):
        if any(not activity.needs_predefined_locations()
               for activity in self.activity_set.all()):
            return "N/A"

        percentage = (
            (100 * self.number_of_complete_locations()) /
            self.number_of_locations())
        return "{percentage:2.0f}%".format(percentage=percentage)

    def is_complete(self):
        """Project is complete if there are any activities, and they are
        complete. A project without any activities is probably being
        setup.

        """
        return self.activity_set.exists() and all(
            activity.is_complete() for activity in self.activity_set.all())

    @cached_property
    def latest_log(self):
        latest_log = UploadLog.latest_for_project(self)
        return latest_log[0] if latest_log else None

    def refresh_hydrovakken(self):
        """Find Hydrovakken shapefiles belonging to this project.
        If there is more than one, return an error message. Otherwise
        refresh the database with the shapefile's contents and return
        any error message from that."""
        shapefiles = list(directories.all_files_in(
            directories.hydrovakken_dir(self), extension='.shp'))

        if len(shapefiles) == 0:
            # No shapefiles is not an error, it's the default.
            return
        if len(shapefiles) > 1:
            return "More than one shapefile found, clean up first."""

        return Hydrovak.reload_from(self, shapefiles[0])

    @property
    def num_open_requests(self):
        from lizard_progress.changerequests.models import Request
        return Request.objects.filter(
            request_status=Request.REQUEST_STATUS_OPEN,
            activity__project=self).count()

    def available_layers(self, user):
        """Yield available map layers for user."""
        from lizard_progress.util.workspaces import MapLayer

        for activity in self.activity_set.all():
            # Obvious use for Python 3's yield from
            for layer in activity.available_layers(user):
                yield layer

        if Hydrovak.objects.filter(project=self).exists():
            yield MapLayer(
                name='Monstervakken {projectname}'.format(projectname=self.name),
                adapter_class='adapter_hydrovak',
                adapter_layer_json=json.dumps({"project_slug": self.slug}),
                extent=None)

    def is_subscribed_to(self, notification_type):
        project_content_type = ContentType.objects.get_for_model(self)
        return NotificationSubscription.objects.filter(
            notification_type=notification_type,
            subscriber_content_type=project_content_type,
            subscriber_object_id=self.id).exists()


class Location(models.Model):
    LOCATION_TYPE_POINT = 'point'
    LOCATION_TYPE_PIPE = 'pipe'
    LOCATION_TYPE_MANHOLE = 'manhole'
    LOCATION_TYPE_DRAIN = 'drain'

    LOCATION_TYPE_CHOICES = (
        (LOCATION_TYPE_POINT, ) * 2,
        (LOCATION_TYPE_PIPE, ) * 2,
        (LOCATION_TYPE_MANHOLE, ) * 2,
        (LOCATION_TYPE_DRAIN, ) * 2,
    )

    # A location / scheduled measurement in an activity
    activity = models.ForeignKey('Activity', null=True)

    location_code = models.CharField(max_length=50, db_index=True)

    location_type = models.CharField(
        max_length=10, default=LOCATION_TYPE_POINT, null=False,
        blank=False, choices=LOCATION_TYPE_CHOICES)

    # Sometimes it needs to be recorded that a location exists, and it
    # should not be impossible to upload data for it, but it's not
    # actually part of the project officialy (think sewer drains that
    # are not owned by the organisation having the drains
    # cleaned). Locations with not_part_of_project True should not count
    # towards progress counts and should be shown differently on the map.
    not_part_of_project = models.BooleanField(default=False)

    # Often unused, but some types of project can plan when a
    # location will be planned.
    planned_date = models.DateField(null=True, blank=True)

    # Geometry can be a point OR a line
    # All Locations of the same location_type must have the same geometry
    # type, because they're all exported to the same shapefile.
    the_geom = models.GeometryField(null=True, srid=SRID)
    is_point = models.BooleanField(default=True)

    # Any extra known information about the location
    information = JSONField(null=True, blank=True)

    timestamp = models.DateTimeField(auto_now=True)
    complete = models.BooleanField(default=False)

    objects = models.GeoManager()

    @property
    def measurement(self):
        """Note: ONLY use this if you are sure there will be only a single
        measurement object per location object you call this on.
        It makes no sense in other situations.

        Returns None if there is no measurement. If there are multiple
        measurements, MultipleObjectsReturned is raised."""
        try:
            return Measurement.objects.get(location=self)
        except Measurement.DoesNotExist:
            return None

    class Meta:
        # Location codes are unique within an activity
        unique_together = ("location_code", "activity")
        ordering = ('location_code',)

    def __unicode__(self):
        if self.location_type:
            u = u'{} {}'.format(
                _(self.location_type).capitalize(),
                self.location_code)
        else:
            u = u"Locatie '%s'" % (self.location_code,)

        if self.complete:
            u += ", {}".format(_(u"complete"))
        elif self.planned_date:
            u += ", {} {}".format(_(u"planned on"), self.planned_date)

        return u

    def get_absolute_url(self):
        """Return an URL that goes to the Map page, zooming to this
        location.

        """
        return reverse(
            'lizard_progress_mapview_location_code',
            kwargs={'activity_id': self.id,
                    'project_slug': self.project.slug,
                    'location_code': self.location_code})

    def plan_location(self, location):
        """Set our geometrical location, IF it wasn't set yet.
        location can be either a Point or a LineString."""
        if hasattr(location, 'ExportToWkt'):
            if is_line(location):
                location = osgeo_3d_line_to_2d_wkt(location)
            else:
                location = osgeo_3d_point_to_2d_wkt(location)

        if self.the_geom is None:
            self.the_geom = location
            self.is_point = not is_line(location)
            self.save()

    def plan_date(self, date):
        """Set a location's planned date. Can't change anymore once
        the location is complete."""
        if not self.complete:
            self.planned_date = date
            self.save()

    def has_measurements(self):

        """Return True if there are any uploaded measurements at this
        location."""
        return self.measurement_set.count() > 0

    def missing_attachments(self):
        return ExpectedAttachment.objects.filter(
            measurements__location=self, uploaded=False)

    @property
    def all_expected_attachments_present(self):
        return not self.missing_attachments().exists()

    def set_completeness(self):
        self.complete = (
            self.has_measurements() and self.all_expected_attachments_present)
        self.save()


class AvailableMeasurementType(models.Model):
    # "Dwarsprofiel", "Oeverfoto", "Oeverkenmerk", "Peilschaal foto",
    # "Peilschaal kenmerk"

    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)

    # Several measurement types can have the same implementation
    # If implementation is '', slug is used instead.
    implementation = models.CharField(max_length=50, unique=False, choices=(
        ('dwarsprofiel', 'dwarsprofiel'),
        ('oeverfoto', 'oeverfoto'),
        ('oeverkenmerk', 'oeverkenmerk'),
        ('foto', 'foto'),
        ('meting', 'meting'),
        ('laboratorium_csv', 'laboratorium_csv'),
        ('ribx_reiniging_riool', 'ribx_reiniging_riool'),
        ('ribx_reiniging_kolken', 'ribx_reiniging_kolken'),
        ('ribx_reiniging_inspectie_riool', 'ribx_reiniging_inspectie_riool'),
    ))

    default_icon_missing = models.CharField(max_length=50)
    default_icon_complete = models.CharField(max_length=50)

    # Can this type be displayed as a map layer / popup?
    # (some day we will need to split that in two, for now this is ok)
    can_be_displayed = models.BooleanField(default=True)

    # If the parser of this measurement type enters newly encountered
    # locations into the database, they don't need to be predefined,
    # and a shape doesn't have to be uploaded before measurements can
    # be uploaded. For most types, however, it'll be True.
    needs_predefined_locations = models.BooleanField(default=True)

    # If needs_predefined_locations is False, but
    # likes_predefined_locations is True, then it depends on the
    # Organization's allows_non_predefined_locations attribute.
    likes_predefined_locations = models.BooleanField(default=False)

    # For most measurement types, there will first be a number of scheduled
    # measurements that will be "filled in" by uploaded measurements. However.
    # it is possible that measurements for some type aren't scheduled, and
    # that the parser for that type enters newly encountered measurements
    # into the database as if they were scheduled right then. In that case,
    # this field will be False and scheduled measurements won't need to
    # be setup in advance.
    needs_scheduled_measurements = models.BooleanField(default=True)

    # Description to show to users, e.g. in the wizard where users can choose
    # measurement types.
    description = models.TextField(default='', blank=True)

    # Sewerage data can be a mix of Point and Line locations, other types
    # are only point data. If lines can be present, change requests are
    # disabled.
    has_only_point_locations = models.BooleanField(default=True)

    # For some measurement types, we keep all versions of uploaded data that
    # have been uploaded. For most, we only keep that last uploaded version.
    keep_updated_measurements = models.BooleanField(default=False)

    @property
    def implementation_slug(self):
        """The implementation details are tied to the slug of the first
        AvailableMeasurementType that implemented it. Later we can add copies
        of the same type that work the same way, they have to have a different
        slug but can have the slug of the reference implementation as their
        implementation."""
        return self.implementation or self.slug

    @property
    def planning_uses_ribx(self):
        return 'ribx' in self.implementation_slug

    class Meta:
        ordering = ('name',)

    def __unicode__(self):
        return self.name

    @classmethod
    def dwarsprofiel(cls):
        return cls.objects.get(slug='dwarsprofiel')


class Activity(models.Model):
    """An activity is a part of a project. Measurements happen as
    part of an activity. All measurements in an activity share the
    same set of locations and the same configuration, and have a
    single measurement type and contractor."""

    project = models.ForeignKey(Project)
    name = models.CharField(max_length=100, default="Activity name")

    measurement_type = models.ForeignKey(
        AvailableMeasurementType, null=True)
    contractor = models.ForeignKey(
        Organization, null=True)

    source_activity = models.ForeignKey(
        'Activity', verbose_name='Activity to copy locations from',
        null=True, blank=True)

    class NoLocationException(Exception):
        pass

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return reverse(
            'lizard_progress_activity_dashboard',
            kwargs={'activity_id': self.id, 'project_slug': self.project.slug})

    def config_value(self, key):
        from lizard_progress import configuration
        config = configuration.Configuration(activity=self)
        return config.get(key)

    def error_configuration(self):
        from lizard_progress import errors
        return errors.ErrorConfiguration(
            self.project, None,
            self.measurement_type)

    def specifics(self):
        return lizard_progress.specifics.Specifics(self.project, self)

    def needs_predefined_locations(self):
        """Is uploading to an unknown location an error in this activity?"""
        if self.measurement_type.needs_predefined_locations:
            return True

        if self.measurement_type.likes_predefined_locations:
            # This means that for this measurement type, it is
            # configurable.
            return self.config_value('use_predefined_locations')

        return False

    def connect_to_activity(self, source_activity):
        self.source_activity = source_activity
        self.save()

        self.copy_locations_from_source_activity()

    def copy_locations_from_source_activity(self):
        if self.source_activity is None:
            return  # Nothing to do

        # Don't copy codes we already have
        own_location_codes = set(
            location.location_code for location in self.location_set.all())

        for location in self.source_activity.location_set.exclude(
                location_code__in=own_location_codes,
                complete=False).prefetch_related('measurement_set'):
            self.copy_location(location)

    def upload_directory(self):
        """Directory where the files for this activity will be stored."""
        return directories.upload_dir(self)

    def can_upload(self, user):
        """User can upload if he is with the contractor, or if user is a
        manager in this project.  """

        return (
            self.project.is_manager(user) or
            self.contractor == Organization.get_by_user(user))

    def num_locations(self):
        return self.location_set.filter(
            not_part_of_project=False).count()

    def num_complete_locations(self):
        return self.location_set.filter(
            complete=True, not_part_of_project=False).count()

    def num_measurements(self):
        return Measurement.objects.filter(
            location__activity=self,
            location__not_part_of_project=False).count()

    def has_measurements(self):
        return self.num_measurements() > 0

    def open_requests(self):
        return self.request_set.filter(request_status=1)

    def copy_location(self, other_location):
        """Copy the other location, IF it already has measurements. Use
        the coordinates of the actual measurement."""
        measurements = list(other_location.measurement_set.all())
        if not measurements:
            return

        # There will be almost always be 1 measurement, and otherwise
        # we have no real way of chosing between them.
        measurement = measurements[0]

        return Location.objects.create(
            activity=self, location_code=other_location.location_code,
            the_geom=measurement.the_geom, complete=False,
            not_part_of_project=other_location.not_part_of_project)

    def get_or_create_location(self, location_code, point):
        try:
            # If it exists, return it
            return Location.objects.get(
                activity=self, location_code=location_code)
        except Location.DoesNotExist:
            # Does it exist in a source activity?
            if self.source_activity is not None:
                try:
                    other_location = Location.objects.get(
                        activity=self.source_activity,
                        location_code=location_code)
                    copied = self.copy_location(other_location)
                    if copied:
                        return copied
                except Location.DoesNotExist:
                    # Pity
                    pass

        # No luck yet. Are locations necessary? If yes, then this
        # is an error.
        if self.needs_predefined_locations():
            raise Activity.NoLocationException()

        # Let's just make one.
        return Location.objects.create(
            activity=self, location_code=location_code,
            the_geom=point, complete=False)

    @classmethod
    def get_unique_activity_name(cls, project, contractor, mtype, activity):
        if not activity:
            # Default
            activity = "{} {}".format(contractor, mtype)

        # Check if name doesn't exist yet
        existing_names = cls.objects.filter(
            project=project).values_list('name', flat=True)

        if activity in existing_names:
            i = 2
            original_activity = activity
            while activity in existing_names:
                activity = "{} ({})".format(original_activity, i)
                i += 1

        return activity

    @cached_property
    def latest_log(self):
        """Return the UploadedLog belonging to this activity with the
        most recent 'when' date, or None if there are no such
        UploadedLogs."""
        latest_log = UploadLog.latest_for_activity(self)
        return latest_log[0] if latest_log else None

    def available_layers(self, user):
        """Yield available map layers."""
        if not has_access(user, self.project, self.contractor):
            return

        if not self.measurement_type.can_be_displayed:
            return

        from lizard_progress.changerequests.models import Request
        for request in self.request_set.filter(
                request_status=Request.REQUEST_STATUS_OPEN):
            yield request.map_layer()

        from lizard_progress.util.workspaces import MapLayer
        yield MapLayer(
            name='%s %s' % (self.project.name, self),
            adapter_class='adapter_progress',
            adapter_layer_json=json.dumps({"activity_id": self.id}),
            extent=None)

    def is_complete(self):
        """An activity is complete if it has more than 0 locations that
        are part of the project, and all of those are complete."""
        if not self.needs_predefined_locations():
            # We can't know whether we are finished.
            return False

        if not self.location_set.filter(not_part_of_project=False).exists():
            # We don't have any locations yet, probably setting up.
            return False

        # Check if any non-complete locations exist
        return not Location.objects.filter(
            activity=self,
            complete=False,
            not_part_of_project=False).exists()

    def notify(self, notification_type, recipients, **kwargs):
        if not self.project.is_subscribed_to(notification_type):
            return False

        if getattr(settings, 'EMAIL_NOTIFICATIONS_EMAIL_ADMINS', False):
            admins = User.objects.filter(
                username__in=getattr(settings, 'USER_ADMINS', []))
            recipients = recipients | admins

        for r in recipients:
            notify.send(
                self,
                notification_type=notification_type,
                recipient=r,
                actor=kwargs.get('actor', None),
                action_object=kwargs.get('action_object', None),
                target=kwargs.get('target', None),
                extra=kwargs.get('extra', None))

    def notify_managers(self, notification_type, **kwargs):
        recipients = self.project.organization.users
        return self.notify(notification_type, recipients, **kwargs)

    def notify_contractors(self, notification_type, **kwargs):
        recipients = self.contractor.users
        return self.notify(notification_type, recipients, **kwargs)


class ExpectedAttachment(models.Model):
    """A filename of a file that has to be uploaded for some
    activity. Measurements have a many to many field to this. Used for
    RIBX, which specifies which media files belong to measurements.

    As this model has no other relations, instances should always be
    connected to at least one Measurement through the many to many
    field. If such a connection is later removed (maybe the
    Measurement was cancelled, or changed), then the
    ExpectedAttachment instance should also be deleted.

    """

    filename = models.CharField(max_length=100)
    uploaded = models.BooleanField(default=False)

    def detach(self, measurement):
        """This attachment is not expected for that measurement anymore. If
        there are no connections to measurements left, delete this
        expected attachment.

        """
        self.measurements.remove(measurement)
        if not self.measurements.all().exists():
            self.delete()

    def register_uploading(self):
        """Called after this file was uploaded. Set uploaded to True, then for
        each measurement that this is attached to, create a new
        measurement object with the original as parent.

        If that completes the measurement's location, set it to complete.
        """
        self.uploaded = True
        self.save()

        measurements = []
        for measurement in self.measurements.all().select_related():
            location = measurement.location
            new_measurement = Measurement.objects.create(
                location=location,
                parent=measurement,
                date=None,
                data={'filetype': 'media'},
                the_geom=None)
            measurements.append(new_measurement)
            location.set_completeness()

        return measurements

    @classmethod
    def register_deletion(cls, activity, path):
        """An uploaded file in some activity was deleted. If that file
        was uploaded as an expected attachment at some point, then we should
        set it to uploaded=False again."""
        filename = os.path.basename(path)

        try:
            expected_attachment = cls.objects.get(
                measurements__location__activity=activity,
                filename__iexact=filename)
        except cls.DoesNotExist:
            return

        expected_attachment.uploaded = False
        expected_attachment.save()

    class Meta:
        ordering = ('uploaded', 'filename', )

    def __unicode__(self):
        return "Expected attachment {} ({}).".format(
            self.filename,
            "uploaded" if self.uploaded else "expected")


class MeasurementTypeAllowed(models.Model):
    """This model is the "through" model for relationships between
    (project-owning) Organizations, and AvailableMeasurementTypes.

    If a combination organization / available measurement type exists,
    then that means that that organization can use this type in *new*
    projects.

    Also, a boolean value stores whether the organization *wants* to
    see this type whenever it creates a new project. Organization admins
    can edit the value of this boolean.
    """
    organization = models.ForeignKey(Organization)
    mtype = models.ForeignKey(AvailableMeasurementType)

    visible = models.BooleanField(default=True)


class Measurement(models.Model):
    """Although most Locations will have only a single associated
    measurement, some will have more because there is only a single
    file associated with a measurement and there are measurement types
    that need multiple files.

    E.g. HDSR's Dwarsprofielen project has a measurement type "fotos"
    that calls for two photos, one of the left bank and one of the
    right bank. That must be represented by two measurements, since
    there are two different files. However, there is only one
    location.

    """

    location = models.ForeignKey(Location, null=True)

    # Dict with the data.
    # Site decides what to store.
    data = JSONField(null=True)

    # The date as retrieved from the measurement data, not the date of
    # uploading.
    date = models.DateTimeField(null=True, blank=True)

    # Any available geometry data in the uploaded measurement.
    the_geom = models.GeometryField(null=True, blank=True, srid=SRID)
    is_point = models.BooleanField(default=True)

    # This is the filename of the uploaded file after it was moved
    # into lizard-progress' archive. Set by process_uploaded_file.
    filename = models.CharField(max_length=1000)

    # Expected Attachments that belong to this Measurement. When they
    # are uploaded, they will get their own Measurement instance, that
    # will have a 'parent' foreignkey to this one.
    expected_attachments = models.ManyToManyField(
        'ExpectedAttachment', related_name='measurements')
    parent = models.ForeignKey('Measurement', null=True)

    # Auto-changes, most likely set in stone the time the file is
    # uploaded.
    timestamp = models.DateTimeField(auto_now=True)

    objects = models.GeoManager()

    def record_location(self, location):
        """Save where this measurement was taken. THEN, plan that
        location in our Location object (only sets it if the location
        didn't have a point yet.

        location can be a Point or a LineString."""
        self.is_point = not is_line(location)

        if hasattr(location, 'ExportToWkt'):
            if self.is_point:
                location = osgeo_3d_point_to_2d_wkt(location)
            else:
                location = osgeo_3d_line_to_2d_wkt(location)
        self.the_geom = location
        self.save()
        self.location.plan_location(location)

    def get_absolute_url(self):
        """Return the URL to the uploaded file that contained this
        measurement."""

        activity = self.location.activity
        return reverse('lizard_progress_filedownload', kwargs={
            'project_slug': activity.project.slug,
            'activity_id': activity.id,
            'measurement_id': self.id,
            'filename': os.path.basename(self.filename)})

    @property
    def base_filename(self):
        return self.filename and os.path.basename(self.filename)

    def delete(self):
        """Delete this measurement. If this is done by a user of the
        contractor organization, this is cancellation (for instance to
        fix errors), if this is done by a user of the project owning
        organisation it means the measurement is not
        approved. Functionally there is no difference -- we undo the
        results of uploading this particular measurement.

        Cancelling a measurement means that any attachments are also
        cancelled, that expected attachments are detached from this
        measurement (and may be removed from the list of expected
        attachments, if they were only attached to this), that the
        location may be marked incomplete once more, and that the
        uploaded file itself may be removed if this was the last
        measurement relating to it. Finally, this measurement will be
        deleted.

        """
        # Once a project is archived, it can't be changed anymore.
        if self.location.activity.project.is_archived:
            raise ValueError(
                "Cannot delete measurements of archived projects.")

        # Detach expected attachments
        for expected_attachment in self.expected_attachments.all():
            expected_attachment.detach(self)

        # Also delete measurements of uploaded attachments related to this
        for measurement in Measurement.objects.filter(parent=self):
            measurement.delete()

        # Delete this
        super(Measurement, self).delete()

        # If no other measurements relate to our filename, delete it
        if (not Measurement.objects.filter(filename=self.filename).exists()):
            if os.path.exists(self.filename):
                os.remove(self.filename)

            # If that happens, and the filename was uploaded as an expected
            # attachment, that attachment should be set uploaded=False again.
            ExpectedAttachment.register_deletion(
                self.location.activity, self.filename)

        # Let our location determine its completeness
        self.location.set_completeness()

    def setup_expected_attachments(self, filenames):

        """This measurement was uploaded, and it included information that
        said that the files in filenames (an iterable of strings)
        will be uploaded for it.

        This function:

        - Makes sure that ExpectedAttachments for these filenames exist,
          and are connected to this Measurement.

        - Disconnects any ExpectedAttachments still attached to this
          Measurement that are not in 'filenames' anymore.

        - Deletes ExpectedAttachments that aren't connected to any
          Measurements anymore due to the previous item.

        Return a boolean that is True if all expected attachments for
        this measurement have been uploaded, or False if there are
        still expected attachments that weren't.

        """
        filenames = set(filenames)

        self.__drop_irrelevant_expected_attachments(filenames)
        self.__attach_relevant_expected_attachments(filenames)

    def __drop_irrelevant_expected_attachments(self, filenames):
        attachments_to_drop = self.expected_attachments.exclude(
            filename__in=filenames)

        for attachment in attachments_to_drop:
            attachment.detach(self)

    def __attach_relevant_expected_attachments(self, filenames):
        activity = self.location.activity

        for filename in filenames:
            try:
                # If the attachment already exists and is attached to this,
                # then that is OK.
                expected_attachment = ExpectedAttachment.objects.get(
                    filename=filename, measurements=self)
            except ExpectedAttachment.DoesNotExist:
                try:
                    # If an attachment with the same filename is
                    # attached to another measurement in the same
                    # activity, then we re-use that; we can't tell
                    # uploaded files with the same filename in the
                    # same activity apart.

                    # *BUT* If that file was already uploaded, then this
                    # leads to a conceptual mess (we would need to create
                    # a Measurement for it too, with this one as parent,
                    # except if this measurement already existed and is
                    # being corrected, because then it may or may not
                    # already exist; but how can we tell? Besides all that,
                    # this is probably unintended by the user anyway,
                    # he just gave two files on two different dates the
                    # same name). So then we raise an exception.
                    expected_attachment = ExpectedAttachment.objects.get(
                        filename=filename,
                        measurements__location__activity=activity)
                    if expected_attachment.uploaded:
                        raise AlreadyUploadedError(filename)

                except ExpectedAttachment.DoesNotExist:
                    # Create a new one.
                    expected_attachment = ExpectedAttachment.objects.create(
                        filename=filename, uploaded=False)
                # Attach it
                self.expected_attachments.add(expected_attachment)

    def missing_attachments(self):
        """Return a queryset of ExpectedAttachments connected to this
        measurement that haven't been uploaded yet."""
        return self.expected_attachments.filter(uploaded=False)

    def attached_measurements(self):
        """Return a queryset of Measurements that have this one as parent."""
        return Measurement.objects.filter(parent=self)

    def __unicode__(self):
        return 'Measurement {} from {}, expects {} attachments'.format(
            self.id, self.filename, self.expected_attachments.count())


class Hydrovak(models.Model):
    """Hydrovak."""
    project = models.ForeignKey(Project)
    br_ident = models.CharField(max_length=100)
    the_geom = models.MultiLineStringField(srid=SRID)
    objects = models.GeoManager()

    def __unicode__(self):
        return unicode(self.br_ident)

    class Meta:
        unique_together = ("project", "br_ident")
        verbose_name_plural = "Monstervakken"
        verbose_name = "Monstervak"

    @classmethod
    def remove_hydrovakken_files(cls, project):
        hydrovakken_dir = directories.hydrovakken_dir(project)
        shutil.rmtree(hydrovakken_dir)
        os.mkdir(hydrovakken_dir)

    @classmethod
    def remove_hydrovakken_data(cls, project):
        cls.objects.filter(project=project).delete()

    @classmethod
    def reload_from(cls, project, shapefile_path):
        cls.remove_hydrovakken_data(project)

        if isinstance(shapefile_path, unicode):
            shapefile_path = shapefile_path.encode('utf8')

        datasource = DataSource(shapefile_path)

        # We only import configuration here, because it imports this module
        # for the OrganizationConfig and ProjectConfig models.
        from lizard_progress import configuration
        id_field_name = configuration.get(
            activity=None, project=project,
            config_option='hydrovakken_id_field')

        layer = datasource[0]

        for feature in layer:
            if id_field_name in feature.fields:
                # The shape can contain both LineStrings and
                # MultiLineStrings - to be able to save both we
                # convert them all to multis
                geom = fromstr(feature.geom.ewkt)
                if isinstance(geom, LineString):
                    geom = MultiLineString(geom)

                hydrovak, created = cls.objects.get_or_create(
                    project=project,
                    br_ident=unicode(feature[id_field_name]),
                    defaults={'the_geom': geom})
                if not created:
                    hydrovak.the_geom = geom
                    hydrovak.save()
            else:
                return (
                    'Veld "{}" niet gevonden in de shapefile. '
                    'Pas de shapefile aan,'
                    'of geef een ander ID veld aan op het Configuratie scherm.'
                    .format(id_field_name))


class UploadedFile(models.Model):
    """This model represents a file that was uploaded.

    An uploaded file will first just be stored and recorded in this
    database table.  Then background tasks will process it -- check
    it, if successful copy it and record it measurements, if not
    successful note that and store error messages in here.

    After this processing, the UploadedFile can in principle be
    deleted. However, it is first kept around so that its status can
    be shown to the user. The user can then decide to clean up the
    status view, and at that point the UploadedFile instances can be
    deleted. The stored uploaded file is deleted at that point as
    well. However, if uploading was successful, then there is a copy
    of it in the file system that will be kept. That is beyond the
    zone of influence of this model.

    Unsuccessful uploaded files can also be re-processed automatically
    by calling re_upload(). A new UploadedFile instance will be
    created, using the same path, and the process uploaded file task
    will be started for this new instance. Because of this, the actual
    uploaded file is only finally deleted if there are no uploadedfile
    instances referring to it anymore."""

    activity = models.ForeignKey(Activity, null=True)

    uploaded_by = models.ForeignKey(User)
    uploaded_at = models.DateTimeField()

    path = models.CharField(max_length=255)

    # If ready is True but success is False, uploading was unsuccessful.
    # In that case, there should be error messages in the UploadedFileError
    # models.

    ready = models.BooleanField(default=False)

    # Success has no meaning while ready is False
    success = models.BooleanField(default=False)

    # A file is linelike if it is text and line numbers make sense
    # (e.g., a .met or .csv file) and False if it is not (like an
    # image).
    linelike = models.BooleanField(default=True)

    class PathDoesNotExist(Exception):
        pass

    def re_upload(self):
        """Make a new UploadedFile instance that refers to the same file,
        and process it. Currently only used if all errors in the original
        file could be treated with possible requests, they were all
        requested and all accepted."""
        new_uf = UploadedFile.objects.create(
            activity=self.activity,
            uploaded_by=self.uploaded_by, uploaded_at=datetime.datetime.now(),
            path=self.path, ready=False, linelike=self.linelike)

        new_uf.schedule_processing()

    def schedule_processing(self):
        """Queue the 'process_uploaded_file' task for this uploaded file when
        the current database transaction has committed, using
        django-transaction-hooks.
        """
        # Need to import here to prevent circular imports
        from . import tasks

        # connection.on_commit is provided by our custom database
        # engine (lizard_progress.db_engine). It takes a callable
        # without arguments, so we use lambda here.
        connection.on_commit(
            lambda: tasks.process_uploaded_file_task.delay(self.id))

    @property
    def filename(self):
        return os.path.basename(self.path)

    def wait_until_path_exists(self, tries=10):
        """Do NOT call from web code! Sleeps up to 10 seconds. Use in
        background tasks."""
        tries_so_far = 0
        while tries_so_far < tries:
            try:
                open(self.path)
                return
            except IOError:
                # We're probably trying too soon, it's not there yet
                tries_so_far += 1
            import time
            time.sleep(1)

        raise UploadedFile.PathDoesNotExist()

    def log_success(self, measurements):
        num_measurements = len(measurements)

        if num_measurements > 0:
            # What can we log... project, contractor, the time, the
            # filename, measurement type, number of measurements
            UploadLog.objects.create(
                activity=self.activity,
                when=datetime.datetime.now(),
                filename=self.filename,
                num_measurements=num_measurements)

    def delete_self(self):
        try:
            if os.path.exists(self.path) and UploadedFile.objects.filter(
                    path=self.path).count() == 1:
                # File exists and only we refer to it
                os.remove(self.path)
            # Try to remove empty directory
            os.rmdir(os.path.dirname(self.path))
        except (IOError, OSError):
            pass

        self.delete()

    def as_dict(self):
        """This will be turned into JSON to send to the UI."""
        return {
            'id': self.id,
            'project_id': self.activity.project.id,
            'activity_id': self.activity.id,
            'uploaded_by': self.get_uploaded_by_name(),
            'uploaded_at': self.uploaded_at.strftime("%d/%m/%y %H:%M"),
            'filename': os.path.basename(self.path),
            'ready': self.ready,
            'success': self.success,
            'error_url': reverse(
                'lizard_progress_uploaded_file_error_view', kwargs=dict(
                    project_slug=self.activity.project.slug,
                    activity_id=self.activity.id,
                    uploaded_file_id=self.id)),
            'delete_url': reverse(
                'lizard_progress_remove_uploaded_file', kwargs={
                    'project_slug': self.activity.project.slug,
                    'uploaded_file_id': self.id
                }),
            'requests_url': reverse(
                'changerequests_possiblerequests', kwargs={
                    'project_slug': self.activity.project.slug,
                    'activity_id': self.activity.id,
                    'uploaded_file_id': self.id
                }),
            'has_possible_requests': self.has_possible_requests()
        }

    def has_possible_requests(self):
        return self.possiblerequest_set.exists()

    def get_uploaded_by_name(self):
        """Return a user's name. Use username if neither first name or last
        name are known."""
        user = self.uploaded_by
        if not user:
            return '?'
        elif user.first_name or user.last_name:
            return user.get_full_name()
        else:
            return user.username

    def is_fixable(self):
        """Return True if the number of errors of this file is equal to
        the number of possible requests."""
        return (
            self.uploadedfileerror_set.count() ==
            self.possiblerequest_set.count())


class UploadedFileError(models.Model):
    uploaded_file = models.ForeignKey(UploadedFile)
    line = models.IntegerField(default=0)  # Always 0 if file is not linelike
    error_code = models.CharField(max_length=100)
    error_message = models.CharField(max_length=300)

    def __unicode__(self):
        return (
            "{file} {line}: {error_code} {error_message}".
            format(file=os.path.basename(self.uploaded_file.path),
                   line=self.line,
                   error_code=self.error_code,
                   error_message=self.error_message))


class ExportRun(models.Model):
    """There can be one export run per combination of activity and exporttype.

    exporttype is usually 'allfiles', but may sometimes be something else
    like 'met' or 'autocad' to make it possilbe to have different ways to
    export the same data."""

    activity = models.ForeignKey(Activity, null=True)

    exporttype = models.CharField(max_length=20)
    # Some export runs generate a file to download, others (the Lizard export)
    # send data somewhere.
    generates_file = models.BooleanField(default=True)

    created_at = models.DateTimeField(null=True, blank=True, default=None)
    created_by = models.ForeignKey(User, null=True, blank=True, default=None)
    file_path = models.CharField(max_length=300, null=True, default=None)
    ready_for_download = models.BooleanField(default=False)
    export_running = models.BooleanField(default=False)

    error_message = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        unique_together = (('activity', 'exporttype'), )

    def __unicode__(self):
        return ("Export '{}' of {}").format(self.exporttype, self.activity)

    @property
    def filename(self):
        return self.file_path and os.path.basename(self.file_path)

    @classmethod
    def get_or_create(cls, activity, exporttype):
        instance, created = cls.objects.get_or_create(
            activity=activity, exporttype=exporttype)
        return instance

    @classmethod
    def all_in_project(cls, project, user):
        """Yield all the export runs user has access to in this
        project."""

        for activity in project.activity_set.all():
            mtype = activity.measurement_type
            if has_access(user, project, activity.contractor):
                if mtype.implementation_slug == 'dwarsprofiel':
                    yield cls.get_or_create(activity, 'met')
                    yield cls.get_or_create(activity, 'dxf')
                    yield cls.get_or_create(activity, 'csv')

                    # Export to Lizard for Almere managers
                    organization = project.organization
                    if (organization.lizard_config and
                            project.is_manager(user)):
                        exportrun = cls.get_or_create(activity, 'lizard')
                        exportrun.generates_file = False
                        exportrun.save()
                        yield exportrun

                for location_type in activity.specifics().location_types:
                    yield cls.get_or_create(
                        activity, '{}shape'.format(location_type))
                yield cls.get_or_create(activity, 'allfiles')

    @property
    def available(self):
        """Check if the results of the export run are available. If
        the export generates a file, see if that is present, otherwise
        check that the export has run."""
        if self.generates_file:
            return self.present
        else:
            return self.created_at is not None

    @property
    def present(self):
        """Check if a file generated by the export run is present. Always false
        if this export run doesn't generate files."""
        return bool(self.file_path and self.ready_for_download and
                    os.path.exists(self.file_path))

    def delete(self):
        """Also delete the file."""
        if self.present:
            os.remove(self.file_path)
        return super(ExportRun, self).delete()

    def clear(self):
        """Make current data unavailable."""
        self.ready_for_download = False
        if self.file_path and os.path.exists(self.file_path):
            os.remove(self.file_path)
        self.file_path = None
        self.save()

    def record_start(self, user):
        self.created_by = user
        self.created_at = datetime.datetime.now()
        self.export_running = True
        self.error_message = None
        self.save()

    def set_ready_for_download(self):
        self.ready_for_download = bool(
            self.file_path and os.path.exists(self.file_path))
        self.export_running = False
        self.save()

    @property
    def up_to_date(self):
        if self.exporttype == 'pointshape':
            return False  # We can't check if it's up to date

        measurement_dates = [
            measurement.timestamp
            for measurement in self.measurements_to_export()
        ]

        return (self.available and
                (not measurement_dates or
                 self.created_at > max(measurement_dates)))

    def measurements_to_export(self):
        return Measurement.objects.filter(
            location__activity=self.activity,
            location__complete=True).select_related()

    def files_to_export(self):
        return set(
            measurement.filename
            for measurement in self.measurements_to_export())

    def export_filename(self, extension="zip"):
        """Return the filename that the result file should use."""
        directory = directories.exports_dir(self.activity)
        return os.path.join(
            directory,
            "{project}-{activityid}-{exporttype}.{extension}").format(
            project=self.activity.project.slug,
            activityid=self.activity.id,
            exporttype=self.exporttype,
            extension=extension).encode('utf8')

    @property
    def nginx_path(self):
        """Path to this export run's file, using '/protected/' as the
        path to the base dir (for Nginx X-Accel-Redirect)."""
        return '{}/{}'.format(
            directories.exports_dir(self.activity, base_dir='/protected'),
            self.filename)

    def fail(self, error_message):
        self.ready_for_download = False
        self.export_running = False
        self.error_message = error_message
        self.save()


class UploadLog(models.Model):
    """Log that a file was correctly uploaded, to show on the front page"""

    activity = models.ForeignKey(Activity)
    when = models.DateTimeField()
    filename = models.CharField(max_length=250)
    num_measurements = models.IntegerField()

    class Meta:
        ordering = ('-when',)

    @classmethod
    def latest_for_project(cls, project, amount=1):
        queryset = cls.objects.filter(activity__project=project)
        return queryset[:amount]

    @classmethod
    def latest_for_activity(cls, activity, amount=1):
        queryset = cls.objects.filter(activity=activity)
        return queryset[:amount]

    def __unicode__(self):
        return "{} uploaded at {} with {} measurements".format(
            self.filename, self.when, self.num_measurements)


# Models for configuration

class OrganizationConfig(models.Model):
    organization = models.ForeignKey(Organization)
    config_option = models.CharField(max_length=50)

    # If an option's 'applies_to_measurement_types' attribute is [],
    # measurement_type must be None. Otherwise, for each slug in that list,
    # all measurement types that have that implementation slug can have
    # an instance in this model.
    measurement_type = models.ForeignKey(AvailableMeasurementType, null=True)
    value = models.CharField(
        'Bij ja/nee opties, voer 1 in voor ja, en niets voor nee.',
        max_length=50, null=True, blank=True)

    def __unicode__(self):
        return "{} for {}: {}".format(
            self.config_option,
            self.measurement_type or "<algemeen>",
            self.value)


class ProjectConfig(models.Model):
    project = models.ForeignKey(Project)
    config_option = models.CharField(max_length=50)
    value = models.CharField(max_length=50, null=True)

    def __unicode__(self):
        return "{}: {}".format(self.config_option, self.value)


class ActivityConfig(models.Model):
    activity = models.ForeignKey(Activity)
    config_option = models.CharField(max_length=50)
    value = models.CharField(max_length=50, null=True)

    def __unicode__(self):
        return "{}: {}".format(self.config_option, self.value)


# Export to Lizard

class LizardConfiguration(models.Model):
    name = models.CharField(max_length=50)
    geoserver_database_engine = models.CharField(max_length=300)
    geoserver_table_name = models.CharField(max_length=50)
    upload_config = models.CharField(max_length=300)
    upload_url_template = models.CharField(max_length=300)

    def __unicode__(self):
        return self.name or self.geoserver_database_engine


@receiver(post_save, sender=Location)
def message_project_complete(sender, instance, **kwargs):
    notification_type = NotificationType.objects.get(name="project voltooid")
    kwargs = {
        'action_object': instance.activity.project,
        'extra': {'link': Site.objects.get_current().domain +
                  instance.activity.project.get_absolute_url(), }
    }
    if instance.complete and instance.activity.project.is_complete():
        return instance.activity.notify_managers(notification_type, **kwargs)


@receiver(post_save, sender=Location)
def message_activity_complete(sender, instance, **kwargs):
    notification_type = NotificationType.objects.get(
        name="werkzaamheid voltooid")
    kwargs = {
        'action_object': instance.activity,
        'target': instance.activity.project,
        'extra': {'link': Site.objects.get_current().domain +
                  instance.activity.get_absolute_url(), }
    }

    if instance.complete and instance.activity.is_complete():
        return instance.activity.notify_managers(notification_type, **kwargs)
