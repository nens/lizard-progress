# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.txt.
# from django.db import models

RDNEW = 28992
SRID = RDNEW

import logging

from django.contrib.gis.db import models
from django.contrib.auth.models import User

from lizard_map.models import JSONField

import lizard_progress.specifics

logger = logging.getLogger(__name__)

class Project(models.Model):
    # "Profielen", "Peilschalen", etc
    name = models.CharField(max_length=50)
    slug = models.SlugField(max_length=50, unique=True)

    # Python class that can accept uploaded files, does checking,
    # and either returns errors or enters the data into the database
    # Something like "hdsr.upload_file"
    # upload_file_class = models.CharField()

    def __unicode__(self):
        return unicode(self.name)

    def specifics(self):
        logger.debug("Asking for specifics...")
        return lizard_progress.specifics.specifics(self)

class Contractor(models.Model):
    # "Tijhuis", "Van der Zwaan", etc
    # Lizard-security can relate these to Django user names?
    project = models.ForeignKey(Project)
    name = models.CharField(max_length=50)
    slug = models.SlugField(max_length=50)
    user = models.ForeignKey(User, null=True, blank=True)

    def __unicode__(self):
        return u"%s in %s" % (self.name, self.project.name)

    
class Area(models.Model):
    # "Noord", "Oost", "Zuid", "West", ...
    project = models.ForeignKey(Project)
    name = models.CharField(max_length=50)
    slug = models.CharField(max_length=50)

    def __unicode__(self):
        return u"%s in %s" % (self.name, self.project.name)

class Location(models.Model):
    # All relevant locations in the project
    unique_id = models.CharField(max_length=50, primary_key=True)

    project = models.ForeignKey(Project)
    area = models.ForeignKey(Area, null=True, blank=True)

    the_geom = models.PointField(null=True, srid=SRID)
    # Any extra known information about the location
    information = JSONField(null=True, blank=True)

    objects = models.GeoManager()

    def __unicode__(self):
        return u"Location with id '%s'" % (self.unique_id,)

class MeasurementType(models.Model):
    # "Dwarsprofiel", "Oeverfoto", "Oeverkenmerk", "Peilschaal foto", "Peilschaal kenmerk"
    project = models.ForeignKey(Project)
    name = models.CharField(max_length=50)
    slug = models.SlugField(max_length=50)

    def __unicode__(self):
        return u"Type '%s' in %s" % (self.name, self.project.name)

class ScheduledMeasurement(models.Model):
    project = models.ForeignKey(Project)
    contractor = models.ForeignKey(Contractor)
    measurement_type = models.ForeignKey(MeasurementType)
    location = models.ForeignKey(Location)

    complete = models.BooleanField()

    @property
    def measurement(self):
        try:
            return Measurement.objects.get(scheduled=self)
        except Measurement.DoesNotExist:
            return None

class Measurement(models.Model):
    scheduled = models.ForeignKey(ScheduledMeasurement)

    # Dict with the data, or image filename/URL, etc.
    # Site decides what to store.
    data = JSONField(null=True)

    date = models.DateTimeField(null=True, blank=True)
    the_geom = models.PointField(null=True, blank=True, srid=SRID)

    objects = models.GeoManager()
