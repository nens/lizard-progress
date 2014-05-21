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
from django.http import HttpRequest
from django.template.defaultfilters import slugify

# JSONField was moved for lizard-map 4.0...
try:
    from jsonfield import JSONField
    JSONField  # Pyflakes...
except ImportError:
    from lizard_map.models import JSONField

import lizard_progress.specifics
from lizard_progress.util import directories

logger = logging.getLogger(__name__)


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
        help_text="The type wil be applied to projects by default")

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
    # means of a data migration.
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
            return cls.objects.get(user=user)
        except cls.DoesNotExist:
            return None

    def __unicode__(self):
        return "{0} {1}".format(self.user.username,
                                self.organization.name)

    def has_role(self, role_code):
        return self.roles.filter(code=role_code).exists()

    def is_manager_in(self, project):
        return self.has_role(UserRole.ROLE_MANAGER) and (
            project.organization == self.organization)

    def roles_description(self):
        return ", ".join(
                UserRole.objects.get(code=code).description
                for code in UserRole.all_role_codes()
                if self.has_role(code))


def has_access(user, project, contractor=None):
    """Test whether user has access to this project (showing data of
    this contractor)."""

    userprofile = UserProfile.get_by_user(user)
    if userprofile is None:
        return False

    if project.is_archived:
        # Only organization's project managers have access
        return (userprofile.organization ==
                project.organization) and (
                    userprofile.has_role(UserRole.ROLE_MANAGER))

    if (userprofile.organization ==
        project.organization):
        # Everybody in the project's organization can see it.
        return True

    # A user may only see projects of other organizations if this user
    # is an Uploader.
    if not userprofile.has_role(UserRole.ROLE_UPLOADER):
        return False

    if contractor:
        # If it is about one contractor's data in this project,
        # it's only visible for that contractor.
        return contractor.organization == userprofile.organization
    else:
        # If this is not about some specific contractor's data,
        # all contractors also have access.
        for c in project.contractor_set.all():
            if c.organization == userprofile.organization:
                return True

    return False


def all_measurements(project, contractor):
    """Return an iterable of all measurements taken for this
    project and contractor."""

    return Measurement.objects.filter(
        scheduled__project=project, scheduled__contractor=contractor)


def current_files(measurements):
    """Given an iterable of measurements, return a set of all
    filenames used to create them.

    One file can contain many measurements, so if we didn't use a set
    we could end up with many duplicates."""

    return set(measurement.filename for measurement in measurements)


class Project(models.Model):
    # "Profielen", "Peilschalen", etc
    name = models.CharField(max_length=50, unique=False,
        verbose_name='projectnaam')
    slug = models.SlugField(max_length=50, unique=True)
    organization = models.ForeignKey(Organization, null=False)
    is_archived = models.BooleanField()
    # Deprecated
    superuser = models.ForeignKey(User, null=True, blank=True,
        verbose_name='projectmanager')
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

    def specifics(self, available_measurement_type=None):
        return lizard_progress.specifics.Specifics(
            self, available_measurement_type)

    def has_measurement_type(self, mtype_slug):
        try:
            MeasurementType.objects.get(
                project=self,
                mtype__slug=mtype_slug)
            return True
        except MeasurementType.DoesNotExist:
            return False

    def needs_predefined_locations(self, available_measurement_type):
        if available_measurement_type.needs_predefined_locations:
            return True

        if available_measurement_type.likes_predefined_locations:
            # We only import configuration here, because it imports this module
            # for the OrganizationConfig and ProjectConfig models below.
            from lizard_progress import configuration
            config = configuration.Configuration(project=self)
            return config.get('use_predefined_locations')

        return False

    def can_upload(self, user):
        """User can upload if he is the superuser or with one of the
        contractors."""

        return (
            self.is_manager(user) or
            Contractor.objects.filter(
                project=self, organization=Organization.get_by_user(user))
            .exists())

    def work_to_do(self):
        """Returns list of contractor/measurement type combinations
        and some statistics about them."""

        contractors = self.contractor_set.all()
        measurement_types = self.measurementtype_set.all()

        info = []

        for c in contractors:
            info_for_contractor = []
            for m in measurement_types:
                if not c.show_measurement_type(m):
                    continue

                scheduled_measurements = len(
                    ScheduledMeasurement.objects.filter(
                        project=self,
                        contractor=c,
                        measurement_type=m))
                if self.needs_predefined_locations(m.mtype):
                    scheduled_measurements = str(scheduled_measurements)
                else:
                    scheduled_measurements = (
                        "{}, vrij uploaden mogelijk".format(
                            scheduled_measurements))

                measurements = Measurement.objects.filter(
                    scheduled__project=self,
                    scheduled__contractor=c,
                    scheduled__measurement_type=m).order_by('timestamp')

                num_m = len(measurements)
                if num_m > 0:
                    last_m = measurements[0].timestamp
                else:
                    last_m = None

                planning_url = (
                    reverse('lizard_progress_planningview', kwargs={
                            'project_slug': self.slug,
                            'contractor_slug': c.slug}) +
                    "?mtype_slug={}".format(m.mtype.slug))

                info_for_contractor.append({
                        'contractor': c,
                        'measurement_type': m,
                        'scheduled_measurements': scheduled_measurements,
                        'planning_url': planning_url,
                        'num_measurements': num_m,
                        'last_measurement': last_m
                        })
            if info_for_contractor:
                info += info_for_contractor
            else:
                planning_url = reverse('lizard_progress_planningview', kwargs={
                        'project_slug': self.slug,
                        'contractor_slug': c.slug})
                info.append({
                        'contractor': c,
                        'measurement_type': None,
                        'scheduled_measurements': "Geen metingen toegewezen",
                        'planning_url': planning_url,
                        'num_measurements': 0,
                        'last_measurement': None
                        })
        return info

    def number_of_scheduled_measurements(self):
        return ScheduledMeasurement.objects.filter(
            project=self).count()

    def number_of_complete_scheduled_measurements(self):
        return ScheduledMeasurement.objects.filter(
            project=self, complete=True).count()

    def percentage_done(self):
        if any(not self.needs_predefined_locations(available_measurement_type)
               for available_measurement_type in
               AvailableMeasurementType.objects.filter(
                measurementtype__project=self)):
            return "N/A"

        percentage = (
            (100 * self.number_of_complete_scheduled_measurements()) /
            self.number_of_scheduled_measurements())
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
        return sum(
            contractor.request_set.filter(request_status=1).count()
            for contractor in self.contractor_set.all())


class Contractor(models.Model):
    # "Tijhuis", "Van der Zwaan", etc
    project = models.ForeignKey(Project)
    name = models.CharField(max_length=50)
    slug = models.SlugField(max_length=50)
    organization = models.ForeignKey(Organization, null=True, blank=True,
        verbose_name='organisatie')

    def set_slug_and_save(self):
        """Call on an unsaved contractor.

        Sets a random slug, saves the project, then sets a new slug
        based on primary key and name."""
        chars = list(string.lowercase)
        random.shuffle(chars)
        self.slug = ''.join(chars)
        self.save()

        self.slug = "{id}-{slug}".format(
            id=self.id,
            slug=slugify(self.organization.name))
        self.save()

    def show_measurement_type(self, measurement_type):
        """Only show that measurement type for this contractor if there are
        scheduled measurements for it, or if all contractors can freely upload
        measurements."""

        if self.project.needs_predefined_locations(measurement_type.mtype):
            return ScheduledMeasurement.objects.filter(
                project=self.project,
                contractor=self,
                measurement_type=measurement_type).exists()
        else:
            return True

    def has_measurements(self):
        return Measurement.objects.filter(
            scheduled__contractor=self).exists()

    def __unicode__(self):
        return u"%s in %s" % (self.organization, self.project.name)

    class Meta:
        unique_together = (("project", "organization"))


class Area(models.Model):
    # "Noord", "Oost", "Zuid", "West", ...
    project = models.ForeignKey(Project)
    name = models.CharField(max_length=50)
    slug = models.CharField(max_length=50)

    def __unicode__(self):
        return u"%s in %s" % (self.name, self.project.name)


class Location(models.Model):
    # All relevant locations in the project
    location_code = models.CharField(max_length=50, db_index=True)
    project = models.ForeignKey(Project)

    area = models.ForeignKey(Area, null=True, blank=True)

    the_geom = models.PointField(null=True, srid=SRID)
    # Any extra known information about the location
    information = JSONField(null=True, blank=True)

    objects = models.GeoManager()

    class Meta:
        # Location codes are unique within a project
        unique_together = (("location_code", "project"))

    def __unicode__(self):
        return u"Location with code '%s'" % (self.location_code,)

    def has_scheduled_measurements(self, mtype=None, contractor=None):
        scheduleds = ScheduledMeasurement.objects.filter(
            location=self)

        if mtype is not None:
            scheduleds = scheduleds.filter(
                measurement_type__mtype=mtype)

        if contractor is not None:
            scheduleds = scheduleds.filter(
                contractor=contractor)

        return scheduleds.count() > 0

    def has_measurements(self, mtype=None, contractor=None):
        """Return True if there are any uploaded measurements at this
        location, for this mtype (=AvailableMeasurementType) or
        contractor, if given."""
        measurements = Measurement.objects.filter(
            scheduled__location=self)

        if mtype is not None:
            measurements = measurements.filter(
                scheduled__measurement_type__mtype=mtype)

        if contractor is not None:
            measurements = measurements.filter(
                scheduled__contractor=contractor)

        return measurements.count() > 0


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
            ('laboratorium_csv', 'laboratorium_csv')))

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


class MeasurementType(models.Model):
    """The way this is implemented now, there is basically a
    many-to-many relationship between AvailableMeasurementType and
    Project, and it is implemented through this table.  Previous
    properties of this model (name and slug) that are now in
    AvailableMeasurementType are available through property functions
    for ease of use and backward compatibility."""

    mtype = models.ForeignKey(AvailableMeasurementType)
    project = models.ForeignKey(Project)

    icon_missing = models.CharField(max_length=50, null=True, blank=True)
    icon_complete = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        # Measurement types occur only once in a project
        unique_together = (("project", "mtype"),)

    @property
    def name(self):
        return self.mtype.name

    @property
    def slug(self):
        return self.mtype.slug

    def __unicode__(self):
        return u"Type '%s' in %s" % (self.mtype.name, self.project.name)

    def has_measurements(self):
        return Measurement.objects.filter(
            scheduled__measurement_type=self).exists()


class ScheduledMeasurement(models.Model):
    project = models.ForeignKey(Project)
    contractor = models.ForeignKey(Contractor)
    measurement_type = models.ForeignKey(MeasurementType)
    location = models.ForeignKey(Location)
    timestamp = models.DateTimeField(auto_now=True)

    complete = models.BooleanField()

    @property
    def measurement(self):
        """Note: ONLY use this if you are sure there will be only a single
        measurement object per scheduledmeasurement object you call this on.
        It makes no sense in other situations.

        Returns None if there is no measurement. If there are multiple
        measurements, MultipleObjectsReturned is raised."""
        try:
            return Measurement.objects.get(scheduled=self)
        except Measurement.DoesNotExist:
            return None

    class Meta:
        unique_together = ("project", "contractor",
            "measurement_type", "location")

    def __unicode__(self):
        return (("Scheduled measurement of type '%s' at location '%s' "
                 "in project '%s' by contractor '%s'.") %
                (self.measurement_type.name, self.location.location_code,
                 self.project.name, self.contractor.name))


class Measurement(models.Model):
    """Although most ScheduledMeasurements will have only a single
    associated measurements, some will have more because there is only
    a single file associated with a measurements.

    E.g. HDSR's Dwarsprofielen project has a measurement type "fotos"
    that calls for two photos, one of the left bank and one of the
    right bank. That must be represented by two measurements, since
    there are two different files. However, there is only one
    scheduled measurement."""

    scheduled = models.ForeignKey(ScheduledMeasurement)

    # Dict with the data.
    # Site decides what to store.
    data = JSONField(null=True)

    # The date as retrieved from the measurement data, not the date of
    # uploading.
    date = models.DateTimeField(null=True, blank=True)

    # Any available geometry data in the uploaded measurement.
    the_geom = models.PointField(null=True, blank=True, srid=SRID)

    # This is the filename of the uploaded file after it was moved
    # into lizard-progress' archive. Set by the upload view.
    filename = models.CharField(max_length=1000)

    # Auto-changes, most likely set in stone the time the file is
    # uploaded.
    timestamp = models.DateTimeField(auto_now=True)

    objects = models.GeoManager()

    @property
    def url(self):
        """Return the URL to the uploaded file that contained this
        measurement."""

        sm = self.scheduled
        return reverse('lizard_progress_filedownload', kwargs={
                    'project_slug': sm.project.slug,
                    'contractor_slug': sm.contractor.slug,
                    'measurement_type_slug': sm.measurement_type.slug,
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
            project, 'hydrovakken_id_field')

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

    project = models.ForeignKey(Project)
    contractor = models.ForeignKey(Contractor)
    uploaded_by = models.ForeignKey(User)
    uploaded_at = models.DateTimeField()

    path = models.CharField(max_length=255)

    # Which measurement type this file was uploaded as, only null for
    # old data.
    mtype = models.ForeignKey(AvailableMeasurementType, null=True)

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
            project=self.project, contractor=self.contractor,
            uploaded_by=self.uploaded_by, uploaded_at=datetime.datetime.now(),
            path=self.path, ready=False, linelike=self.linelike,
            mtype=self.mtype)

        from . import tasks
        tasks.process_uploaded_file_task.delay(new_uf.id)

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
                project=self.project,
                uploading_organization=self.contractor.organization,
                when=datetime.datetime.now(),
                filename=self.filename,
                mtype=measurements[0].scheduled.measurement_type.mtype,
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
            'project_id': self.project.id,
            'contractor_id': self.contractor.id,
            'uploaded_by': self.uploaded_by.get_full_name(),
            'uploaded_at': self.uploaded_at.strftime("%d/%m/%y %H:%M"),
            'filename': os.path.basename(self.path),
            'ready': self.ready,
            'success': self.success,
            'error_url': reverse(
                'lizard_progress_uploaded_file_error_view', args=(self.id,)),
            'delete_url': reverse(
                'lizard_progress_remove_uploaded_file', kwargs={
                    'project_slug': self.project.slug,
                    'uploaded_file_id': self.id
                    }),
            'requests_url': reverse(
                'changerequests_possiblerequests', kwargs={
                    'project_slug': self.project.slug,
                    'uploaded_file_id': self.id
                    }),
            'has_possible_requests': self.has_possible_requests()
            }

    def has_possible_requests(self):
        return self.possiblerequest_set.exists()

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

    project = models.ForeignKey(Project)
    contractor = models.ForeignKey(Contractor)
    measurement_type = models.ForeignKey(AvailableMeasurementType)
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
        unique_together = (
            'project', 'contractor', 'measurement_type', 'exporttype')

    def __unicode__(self):
        return ("Export '{exporttype}' of all data of type "
                "'{measurement_type}' by {contractor} in {project}"
                ).format(
            exporttype=self.exporttype,
            contractor=self.contractor.organization,
            project=self.project,
            measurement_type=self.measurement_type)

    @property
    def measurement_type_in_project(self):
        """Returns the MeasurementType connected to this export run's project
        and AvailableMeasurementType."""
        try:
            return MeasurementType.objects.get(
                project=self.project, mtype=self.measurement_type)
        except MeasurementType.DoesNotExist:
            return None

    @property
    def filename(self):
        return self.file_path and os.path.basename(self.file_path)

    @classmethod
    def get_or_create(cls, project, contractor, measurement_type, exporttype):
        instance, created = cls.objects.get_or_create(
            project=project, contractor=contractor,
            measurement_type=measurement_type, exporttype=exporttype)
        return instance

    @classmethod
    def all_in_project(cls, project, user):
        """Yield all the export runs user has access to in this
        project."""
        mtypes = MeasurementType.objects.filter(project=project)
        contractors = Contractor.objects.filter(project=project)

        for mtype in mtypes:
            for contractor in contractors:
                if has_access(user, project, contractor):
                    if mtype.mtype.implementation_slug == 'dwarsprofiel':
                        yield cls.get_or_create(
                            project, contractor, mtype.mtype, 'met')
                        yield cls.get_or_create(
                            project, contractor, mtype.mtype, 'dxf')
                        yield cls.get_or_create(
                            project, contractor, mtype.mtype, 'csv')

                        # Export to Lizard for Almere superusers
                        organization = project.organization
                        if (organization.lizard_config and
                            project.superuser == user):
                            exportrun = cls.get_or_create(
                                project, contractor, mtype.mtype, 'lizard')
                            exportrun.generates_file = False
                            exportrun.save()
                            yield exportrun

                    yield cls.get_or_create(
                        project, contractor, mtype.mtype, 'allfiles')
                    yield cls.get_or_create(
                        project, contractor, mtype.mtype, 'pointshape')

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
            scheduled__project=self.project,
            scheduled__contractor=self.contractor,
            scheduled__measurement_type__mtype=self.measurement_type,
            scheduled__complete=True).select_related()

    def files_to_export(self):
        return set(
            measurement.filename
            for measurement in self.measurements_to_export())

    def export_filename(self, extension="zip"):
        """Return the filename that the result file should use."""
        directory = directories.exports_dir(self.project, self.contractor)
        return os.path.join(
            directory,
            "{project}-{contractor}-{mtype}.{extension}").format(
            project=self.project.slug,
            contractor=self.contractor.slug,
            mtype=self.measurement_type.slug,
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
        queryset = cls.objects.filter(project=project)
        if queryset.exists():
            return queryset[:amount]
        else:
            return None


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


# Export to Lizard

class LizardConfiguration(models.Model):
    name = models.CharField(max_length=50)
    geoserver_database_engine = models.CharField(max_length=300)
    geoserver_table_name = models.CharField(max_length=50)
    upload_config = models.CharField(max_length=300)
    upload_url_template = models.CharField(max_length=300)

    def __unicode__(self):
        return self.name or self.geoserver_database_engine
