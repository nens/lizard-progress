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
import logging
import os
import random
import string

from django.contrib.auth.models import User
from django.contrib.gis.db import models
from django.core.urlresolvers import reverse
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

    # Organizations are _either_ project owners or uploaders, never both
    is_project_owner = models.BooleanField(default=False)

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

    def __unicode__(self):
        return self.name

    def set_error_codes(self, codes):
        for code in codes:
            error = ErrorMessage.objects.get(error_code=code)
            self.errors.add(error)


class UserProfile(models.Model):
    user = models.ForeignKey(User, unique=True)
    organization = models.ForeignKey(Organization)

    @classmethod
    def get_by_user(cls, user):
        if not user.is_authenticated():
            return None
        try:
            return cls.objects.get(user=user)
        except cls.DoesNotExist:
            return None

    def __unicode__(self):
        return "{0} {1}".format(self.user.username,
                                self.organization.name)


def has_access(user, project, contractor=None):
    """Test whether user has access to this project (showing data of
    this contractor)."""

    if user.is_anonymous():
        # Not logged in
        return False

    if user.is_superuser:
        # Site superuser
        return True

    if project.superuser == user:
        # Project superuser
        return True

    userprofile = UserProfile.objects.get(user=user)
    if contractor:
        return contractor.organization == userprofile.organization
    else:
        # If this is not about some specific contractor's data,
        # all contractors have access.
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
    name = models.CharField(max_length=50, unique=True,
        verbose_name='projectnaam')
    slug = models.SlugField(max_length=50, unique=True)
    superuser = models.ForeignKey(User, null=True, blank=True,
        verbose_name='projectmanager')

    class Meta:
        ordering = ('name',)

    def __unicode__(self):
        return unicode(self.name)

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

    def specifics(self):
        return lizard_progress.specifics.Specifics(self)

    def has_measurement_type(self, mtype_slug):
        try:
            MeasurementType.objects.get(
                project=self,
                mtype__slug=mtype_slug)
            return True
        except MeasurementType.DoesNotExist:
            return False

    @property
    def organization(self):
        return Organization.objects.get(
            userprofile__user=self.superuser)

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
        contractors.  Slightly different from has_access, because
        admin isn't included."""

        return (user == self.superuser or Contractor.objects.filter(
                project=self, organization__userprofile__user=user).exists())

    def work_to_do(self):
        """Returns list of contractor/measurement type combinations
        and some statistics about them."""

        contractors = self.contractor_set.all()
        measurement_types = self.measurementtype_set.all()

        info = []

        for m in measurement_types:
            for c in contractors:
                if self.needs_predefined_locations(m.mtype):
                    scheduled_measurements = len(
                        ScheduledMeasurement.objects.filter(
                            project=self,
                            contractor=c,
                            measurement_type=m))
                else:
                    scheduled_measurements = "N/A"

                measurements = ScheduledMeasurement.objects.filter(
                    project=self,
                    contractor=c,
                    measurement_type=m,
                    complete=True).order_by('timestamp')

                num_m = len(measurements)
                if num_m > 0:
                    last_m = measurements[0].timestamp
                else:
                    last_m = None

                info.append({
                        'contractor': c,
                        'measurement_type': m,
                        'scheduled_measurements': scheduled_measurements,
                        'num_measurements': num_m,
                        'last_measurement': last_m
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

        percentage = ((100 * self.number_of_scheduled_measurements()) /
                      self.number_of_complete_scheduled_measurements())
        return "{percentage:2.0f}%".format(percentage=percentage)

    def latest_log(self):
        if not hasattr(self, '_latest_log'):
            latest_log = UploadLog.latest(self)
            self._latest_log = latest_log[0] if latest_log else None

        return self._latest_log


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
        scheduled measurements for it."""
        return ScheduledMeasurement.objects.filter(
            project=self.project,
            contractor=self,
            measurement_type=measurement_type).exists()

    def __unicode__(self):
        return u"%s in %s" % (self.name, self.project.name)

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


class AvailableMeasurementType(models.Model):
    # "Dwarsprofiel", "Oeverfoto", "Oeverkenmerk", "Peilschaal foto",
    # "Peilschaal kenmerk"

    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)
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

    def __unicode__(self):
        return self.name

    @classmethod
    def dwarsprofiel(cls):
        return cls.objects.get(slug='dwarsprofiel')


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
    br_ident = models.CharField(max_length=24)
    the_geom = models.LineStringField(srid=SRID)
    objects = models.GeoManager()

    def __unicode__(self):
        return unicode(self.br_ident)

    class Meta:
        unique_together = ("project", "br_ident")
        verbose_name_plural = "Hydrovakken"


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
    zone of influence of this model."""

    project = models.ForeignKey(Project)
    contractor = models.ForeignKey(Contractor)
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

    @property
    def filename(self):
        return os.path.basename(self.path)

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
        if os.path.exists(self.path):
            os.remove(self.path)
        self.delete()

    def as_dict(self):
        """This will be turned into JSON to send to the UI."""
        return {
            'id': self.id,
            'project_id': self.project.id,
            'contractor_id': self.contractor.id,
            'uploaded_by': self.uploaded_by.get_full_name(),
            'uploaded_at': unicode(self.uploaded_at),
            'filename': os.path.basename(self.path),
            'ready': self.ready,
            'success': self.success,
            'error_url': reverse(
                'lizard_progress_uploaded_file_error_view', args=(self.id,)),
            'delete_url': reverse(
                'lizard_progress_remove_uploaded_file', kwargs={
                    'project_slug': self.project.slug,
                    'uploaded_file_id': self.id
                    })
            }


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

    created_at = models.DateTimeField(null=True, blank=True, default=None)
    created_by = models.ForeignKey(User, null=True, blank=True, default=None)
    file_path = models.CharField(max_length=300, null=True, default=None)
    ready_for_download = models.BooleanField(default=False)
    export_running = models.BooleanField(default=False)

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
                    if mtype.slug == 'dwarsprofiel':
                        yield cls.get_or_create(
                            project, contractor, mtype.mtype, 'met')
                        yield cls.get_or_create(
                            project, contractor, mtype.mtype, 'dxf')
                        yield cls.get_or_create(
                            project, contractor, mtype.mtype, 'csv')

                    yield cls.get_or_create(
                        project, contractor, mtype.mtype, 'allfiles')

    @property
    def present(self):
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
        self.save()

    def set_ready_for_download(self):
        self.ready_for_download = bool(
            self.file_path and os.path.exists(self.file_path))
        self.export_running = False
        self.save()

    @property
    def up_to_date(self):
        measurement_dates = [
            measurement.timestamp
            for measurement in self.measurements_to_export()
            ]

        return (self.present and
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


class UploadLog(models.Model):
    """Log that a file was correctly uploaded, to show on the front page"""

    project = models.ForeignKey(Project)
    uploading_organization = models.ForeignKey(Organization)
    mtype = models.ForeignKey(AvailableMeasurementType)

    when = models.DateTimeField()
    filename = models.CharField(max_length=50)
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
