# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

# Python 3 is coming
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

RDNEW = 28992
SRID = RDNEW

import datetime
import functools
import logging
import os
import random
import shutil
import string

from django.contrib.auth.models import User
from django.contrib.gis.db import models
from django.contrib.gis.geos import LineString
from django.contrib.gis.geos import MultiLineString
from django.contrib.gis.geos import fromstr
from django.contrib.gis.gdal import DataSource
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.db import connection
from django.http import HttpRequest
from django.template.defaultfilters import slugify

from jsonfield import JSONField

import lizard_progress.specifics
from lizard_progress.util import directories

logger = logging.getLogger(__name__)


def is_line(geom):
    """Decide whether geom is a line geometry (of several possible types)."""
    if isinstance(geom, LineString):
        # django.contrib.gis.geos.LineString
        return True

    if hasattr(geom, 'ExportToWkt') and 'LINESTRING' in geom.ExportToWkt():
        # osgeo.ogr.Geometry linestring
        return True

    return False


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

    @classmethod
    def users_in_same_organization(cls, user):
        """Returns a list of user in same organization."""
        organization = UserProfile.objects.get(user=user).organization
        userprofiles = UserProfile.objects.filter(organization=organization)
        users = [profile.user for profile in userprofiles]
        return users

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
    ROLE_MANAGER = "manager"  # Can make new projects, configure
                              # running projects
    # ROLE_VIEWER = "viewer"  # This role is commented out because right
                            # now I *think* we can keep this implicit
                            # -- all members of an organization are
                            # viewers.
    ROLE_UPLOADER = "uploader"  # Can upload measurements and reports
                                # if user's organization is a
                                # contractor in the project
    ROLE_ADMIN = "admin"  # Can assign roles to people in the
                          # organization, create and delete user
                          # accounts belonging to this organization.

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
    slug = models.SlugField(max_length=50, unique=True)
    organization = models.ForeignKey(Organization, null=False)
    is_archived = models.BooleanField(default=False)

    project_type = models.ForeignKey(ProjectType, null=True, blank=True)
    created_at = models.DateTimeField(default=datetime.datetime.now)

    class Meta:
        ordering = ('name',)
        unique_together = [('name', 'organization')]

    def __unicode__(self):
        return unicode(self.name)

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
        return Location.objects.filter(activity__project=self).count()

    def number_of_complete_locations(self):
        return Location.objects.filter(
            activity__project=self, complete=True).count()

    def percentage_done(self):
        if any(activity.needs_predefined_locations()
               for activity in self.activity_set.all()):
            return "N/A"

        percentage = (
            (100 * self.number_of_complete_locations()) /
            self.number_of_locations())
        return "{percentage:2.0f}%".format(percentage=percentage)

    def latest_log(self):
        if not hasattr(self, '_latest_log'):
            latest_log = UploadLog.latest(self)
            self._latest_log = latest_log[0] if latest_log else None

        return self._latest_log

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


class Location(models.Model):
    # A location / scheduled measurement in an activity
    activity = models.ForeignKey('Activity', null=True)

    location_code = models.CharField(max_length=50, db_index=True)

    # Geometry can be a point OR a line
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
        return u"Location with code '%s'" % (self.location_code,)

    def plan_location(self, location):
        """Set our geometrical location, IF it wasn't set yet.
        location can be either a Point or a LineString."""
        if self.the_geom is None:
            self.the_geom = location
            self.is_point = not is_line(location)
            self.save()

    def has_measurements(self):
        """Return True if there are any uploaded measurements at this
        location."""
        return self.measurement_set.count() > 0


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
        ('ribx', 'ribx')))

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
        return directories.activity_dir(self)

    def can_upload(self, user):
        """User can upload if he is with the contractor, or if user is a
        manager in this project.  """

        return (
            self.project.is_manager(user)
            or self.contractor == Organization.get_by_user(user))

    def num_locations(self):
        return self.location_set.all().count()

    def num_complete_locations(self):
        return self.location_set.filter(complete=True).count()

    def num_measurements(self):
        return Measurement.objects.filter(
            location__activity=self).count()

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
            the_geom=measurement.the_geom, complete=False)

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

    def latest_upload(self):
        """Return the UploadedFile belonging to this activity with the
        most recent 'uploaded_at' date, or None if there are no such
        UploadedFiles."""
        files = list(self.uploadedfile_set.order_by('-uploaded_at')[:1])

        if files:
            return files[0]
        else:
            return None


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

    # Auto-changes, most likely set in stone the time the file is
    # uploaded.
    timestamp = models.DateTimeField(auto_now=True)

    objects = models.GeoManager()

    def record_location(self, location):
        """Save where this measurement was taken. THEN, plan that
        location in our Location object (only sets it if the location
        didn't have a point yet.

        location can be a Point or a LineString."""
        self.the_geom = location
        self.is_point = not is_line(location)
        self.save()
        self.location.plan_location(location)

    @property
    def url(self):
        """Return the URL to the uploaded file that contained this
        measurement."""

        activity = self.location.activity
        return reverse('lizard_progress_filedownload', kwargs={
            'project_slug': activity.project.slug,
            'activity_id': activity.id,
            'filename': os.path.basename(self.filename)})


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
        verbose_name_plural = "Hydrovakken"

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
                project=self.activity.project,
                uploading_organization=self.activity.contractor,
                when=datetime.datetime.now(),
                filename=self.filename,
                mtype=self.activity.measurement_type,
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
    """There can be one export run per combination of project,
    contractor, measurement type, exporttype.

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

                yield cls.get_or_create(activity, 'allfiles')
                yield cls.get_or_create(activity, 'pointshape')

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
        return bool(self.file_path and self.ready_for_download
                    and os.path.exists(self.file_path))

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
                (not measurement_dates
                 or self.created_at > max(measurement_dates)))

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
            "{project}-{activityid}-{contractor}-{mtype}.{extension}").format(
            project=self.activity.project.slug,
            activityid=self.activity.id,
            contractor=self.activity.contractor.slug,
            mtype=self.activity.measurement_type.slug,
            extension=extension).encode('utf8')

    def fail(self, error_message):
        self.ready_for_download = False
        self.export_running = False
        self.error_message = error_message
        self.save()


class UploadLog(models.Model):
    """Log that a file was correctly uploaded, to show on the front page"""

    project = models.ForeignKey(Project)
    uploading_organization = models.ForeignKey(Organization)
    mtype = models.ForeignKey(AvailableMeasurementType)

    when = models.DateTimeField()
    filename = models.CharField(max_length=250)
    num_measurements = models.IntegerField()

    class Meta:
        ordering = ('when',)

    @classmethod
    def latest(cls, project, amount=1):
        queryset = cls.objects.filter(project=project).select_related(
            'uploading_organization')
        return queryset[:amount]


### Models for configuration

class OrganizationConfig(models.Model):
    organization = models.ForeignKey(Organization)
    config_option = models.CharField(max_length=50)
    value = models.CharField(
        'Bij ja/nee opties, voer 1 in voor ja, en niets voor nee.',
        max_length=50, null=True, blank=True)


class ProjectConfig(models.Model):
    project = models.ForeignKey(Project)
    config_option = models.CharField(max_length=50)
    value = models.CharField(max_length=50, null=True)


class ActivityConfig(models.Model):
    activity = models.ForeignKey(Activity)
    config_option = models.CharField(max_length=50)
    value = models.CharField(max_length=50, null=True)


# Export to Lizard

class LizardConfiguration(models.Model):
    name = models.CharField(max_length=50)
    geoserver_database_engine = models.CharField(max_length=300)
    geoserver_table_name = models.CharField(max_length=50)
    upload_config = models.CharField(max_length=300)
    upload_url_template = models.CharField(max_length=300)

    def __unicode__(self):
        return self.name or self.geoserver_database_engine
