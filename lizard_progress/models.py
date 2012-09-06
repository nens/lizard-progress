# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.txt.
# from django.db import models

RDNEW = 28992
SRID = RDNEW

import logging
import os

from django.contrib.gis.db import models
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse

# JSONField was moved for lizard-map 4.0...
try:
    from lizard_map.fields import JSONField
    JSONField  # Pyflakes...
except ImportError:
    from lizard_map.models import JSONField

import lizard_progress.specifics

logger = logging.getLogger(__name__)


def has_access(user, project, contractor=None):
    """Test whether user has access to this project (showing data of
    this contractor).

    Should probably be implemented using lizard-security but I lack
    the time to figure that out right now."""

    if user.is_anonymous():
        # Not logged in
        return False

    if user.is_superuser:
        # Site superuser
        return True

    if project.superuser == user:
        # Project superuser
        return True

    if contractor:
        return contractor.user == user
    else:
        # If this is not about some specific contractor's data,
        # all contractors have access.
        for c in project.contractor_set.all():
            if c.user == user:
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

    def __unicode__(self):
        return unicode(self.name)

    def specifics(self):
        return lizard_progress.specifics.Specifics(self)


class Contractor(models.Model):
    # "Tijhuis", "Van der Zwaan", etc
    project = models.ForeignKey(Project)
    name = models.CharField(max_length=50)
    slug = models.SlugField(max_length=50)
    user = models.ForeignKey(User, null=True, blank=True,
        verbose_name='loginnaam')

    def __unicode__(self):
        return u"%s in %s" % (self.name, self.project.name)

    class Meta:
        unique_together = (("project", "slug"))


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
