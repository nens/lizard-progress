# -*- coding: utf-8 -*-
# Copyright 2011 Nelen & Schuurmans

"""Command that goes through all the uploaded data (most recent
versions only) and runs the parser checks again. This should be used
if the parser checks have changed after some data has been uploaded
already. If the parser hasn't changed, there should be no need."""

import os
import zipfile

from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

from lizard_progress import models
from lizard_progress.models import all_measurements
from lizard_progress.models import current_files
from lizard_progress.tools import MovedFile


def add_to_zipfile(project, organization, measurement_type):
    """Iterate over all files, get parsers for them, try the parsers
    on the files.

    Returned is a list of errors, in the form of 3-tuples
    (current-file-path, original-filename, error-message)."""

    if measurement_type:
        mtypes = (measurement_type,)
    else:
        mtypes = tuple(models.MeasurementType.objects.filter(project=project))

    zipped = zipfile.ZipFile("files.zip", "w")

    for mtype in mtypes:
        files = current_files(
            all_measurements(project, organization).
            filter(scheduled__available_measurement_type=mtype))
        for path in files:
            with MovedFile(path) as moved_file:
                archive_filename = os.path.join(mtype.mtype.slug,
                                                os.path.basename(moved_file))
                print archive_filename
                zipped.write(path, archive_filename)
    zipped.close()


class Command(BaseCommand):
    """Command that goes through all uploaded data and re-checks it."""

    args = "<projectid> <organizationid> [<measurementtypeid>]"
    help = """Command that goes through all the uploaded data (most
recent versions only) and runs the parser checks again. This should be
used if the parser checks have changed after some data has been
uploaded already. If the parser hasn't changed, there should be no
need.

This command only shows one error message per file, checking stops at
the first error."""

    def handle(self, *args, **options):
        """Run the command."""

        self.check_arguments(args)
        add_to_zipfile(
            self.project, self.organization, self.measurement_type)

    def check_arguments(self, args):
        """Check the arguments. Errors write some information to
        stderr, then raise CommandError with the actual error."""

        if len(args) > 3:
            self.stderr.write("Arguments: %s.\n" % (self.args,))
            raise CommandError("Too many arguments.")

        if not args:
            self.stderr.write("Arguments: %s.\n" % (self.args,))
            projects = models.Project.objects.all()
            if projects:
                self.stderr.write("Available projects:\n")
                for project in projects:
                    self.stderr.write(
                        "{}: {}\n".format(project.id, project.name))
            raise CommandError("No project id given.")

        try:
            self.project = models.Project.objects.get(pk=args[0])
        except models.Project.DoesNotExist:
            raise CommandError("Project '%s' does not exist." % (args[0],))

        if len(args) == 1:
            self.stderr.write("Arguments: %s.\n" % (self.args,))
            organizations = models.Organization.objects.filter(
                activity__project=self.project)

            if organizations:
                self.stderr.write(
                    "Available contractors for project {}:\n"
                    .format(self.project.name))
                for organization in organizations:
                    self.stderr.write(
                        "{}: {}".format(organization.id, organization))
            raise CommandError("No contractor id given.")

        try:
            self.organization = models.Organization.objects.get(pk=args[1])
        except models.organization.DoesNotExist:
            raise CommandError(
                "Organization '%s' does not exist." % (args[1],))

        if len(args) != 2:
            try:
                self.measurement_type = (
                    models.AvailableMeasurementType.objects.get(
                        pk=args[2], activity__project=self.project))

            except models.AvailableMeasurementType.DoesNotExist:
                raise CommandError(
                    ("Measurement type given, but id '%s' does not"
                     " exist in project '%s'.") %
                    (args[2], str(self.project)))
        else:
            self.measurement_type = None
