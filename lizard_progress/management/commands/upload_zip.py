# -*- coding: utf-8 -*-
# Copyright 2014 Nelen & Schuurmans

"""Contains hackery that makes it only work for Peilschalen. Need to
move them from the old HDSR upload server."""

import datetime
import os
import tempfile
import zipfile

from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

import Image

from lizard_map.coordinates import wgs84_to_rd
from lizard_progress import models
from lizard_progress import tasks
from lizard_progress.util.image import get_exif_data, get_lat_lon


def scheduled_measurement_for_jpg(project, contractor, filepath):
    if filepath.upper().endswith('JPG'):
        mtype_slug = 'foto'
    else:
        return

    measurement_type = models.MeasurementType.objects.get(
        project=project, mtype__slug=mtype_slug)

    im = Image.open(filepath)
    exif_data = get_exif_data(im)
    lat, lon = get_lat_lon(exif_data)

    x, y = wgs84_to_rd(lon, lat)

    uniek_id = os.path.splitext(os.path.basename(filepath))[0].upper()
    location, created = models.Location.objects.get_or_create(
        location_code=uniek_id,
        project=project)
    location.the_geom = "POINT ({} {})".format(x, y)
    location.save()

    models.ScheduledMeasurement.objects.get_or_create(
        project=project,
        contractor=contractor,
        location=location,
        measurement_type=measurement_type)


def upload_zipfile(stdout, project, contractor, path):
    """Create a temporary directory; unzip the zipfile in there;
    create UploadedFile objects for each file; start the background
    task for each file."""
    basedir = os.path.join(
        settings.BUILDOUT_DIR, 'var', 'lizard_progress', 'uploaded_files')
    tmpdir = tempfile.mkdtemp(dir=basedir)
    zipf = zipfile.ZipFile(path)
    zipf.extractall(tmpdir)

    # Get a user
    profiles = list(models.UserProfile.objects.filter(
            organization=contractor.organization))

    if not profiles:
        raise CommandError("This contractor has no users!")

    user = profiles[0].user
    stdout.write("Uploading as user {}...\n".format(user))

    for (dirpath, dirnames, filenames) in os.walk(tmpdir):
        for filename in filenames:
            fullpath = os.path.join(dirpath, filename)
            if fullpath.lower().endswith('jpg'):
                scheduled_measurement_for_jpg(project, contractor, fullpath)

            uploaded_file = models.UploadedFile.objects.create(
                project=project,
                contractor=contractor,
                uploaded_by=user,
                uploaded_at=datetime.datetime.now(),
                path=fullpath)
            tasks.process_uploaded_file_task.delay(uploaded_file.id)
            stdout.write("{} uploaded.\n".format(filename))


class Command(BaseCommand):
    """Command that goes through all uploaded data and re-checks it."""

    args = "<organizationslug> <projectslug> <contractorslug> <zipfilename>"
    help = """Unzip a zipfile and "upload" each file."""

    def handle(self, *args, **options):
        """Run the command."""

        self.check_arguments(args)
        upload_zipfile(
            self.stdout, self.project, self.contractor, self.zipfile_path)

    def check_arguments(self, args):
        """Check the arguments. Errors write some information to
        stderr, then raise CommandError with the actual error."""

        if len(args) > 4:
            self.stderr.write("Arguments: %s.\n" % (self.args,))
            raise CommandError("Wrong number of arguments.")

        if not args:
            self.stderr.write("Arguments: %s.\n" % (self.args,))
            organizations = models.Organization.objects.all()
            if organizations:
                self.stderr.write("Available organizations:\n")
                for org in sorted(organizations, key=lambda o: o.name):
                    self.stderr.write("- {}\n".format(org.name))
            raise CommandError("No organization given.")

        try:
            self.organization = models.Organization.objects.get(name=args[0])
        except models.Organization.DoesNotExist:
            raise CommandError(
                "Organization '%s' does not exist." % (args[0],))

        if len(args) == 1:
            self.stderr.write("Arguments: %s.\n" % (self.args,))
            projects = models.Project.objects.filter(
                organization=self.organization)
            if projects:
                self.stderr.write("Available projects:\n")
                for project in sorted(projects, key=lambda p: p.slug):
                    self.stderr.write("- %s\n" % (project.slug,))
            raise CommandError("No project slug given.")

        try:
            self.project = models.Project.objects.get(
                organization=self.organization, slug=args[1])
        except models.Project.DoesNotExist:
            raise CommandError("Project '%s' does not exist." % (args[1],))

        if len(args) == 2:
            self.stderr.write("Arguments: %s.\n" % (self.args,))
            contractors = models.Contractor.objects.filter(
                project=self.project)
            if contractors:
                self.stderr.write("Available contractors for project %s:\n" %
                                  (self.project.slug,))
                for contractor in contractors:
                    self.stderr.write("- %s\n" % (contractor.slug,))
            raise CommandError("No contractor slug given.")

        try:
            self.contractor = models.Contractor.objects.get(
                project=self.project, slug=args[2])
        except models.Contractor.DoesNotExist:
            raise CommandError("Contractor '%s' does not exist." % (args[2],))

        if len(args) == 3:
            self.stderr.write("Arguments: %s.\n" % (self.args,))
            raise CommandError("No zipfile given.")

        self.zipfile_path = args[3]
        if not os.path.exists(self.zipfile_path):
            raise CommandError("{} does not exist.".format(self.zipfile_path))
