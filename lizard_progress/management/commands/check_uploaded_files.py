# -*- coding: utf-8 -*-
# Copyright 2011 Nelen & Schuurmans

"""Command that goes through all the uploaded data (most recent
versions only) and runs the parser checks again. This should be used
if the parser checks have changed after some data has been uploaded
already. If the parser hasn't changed, there should be no need."""

import os
import shutil

from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

from lizard_progress.views import orig_from_unique_filename
from lizard_progress import models
from lizard_progress.specifics import parser_factory


def all_measurements(project, contractor):
    """Return an iterable of all measurements taken for this
    project and contractor."""

    return models.Measurement.objects.filter(
        scheduled__project=project, scheduled__contractor=contractor)


def current_files(measurements):
    """Given an iterable of measurements, return a set of all
    filenames used to create them.

    One file can contain many measurements, so if we didn't use a set
    we could end up with many duplicates."""

    return set(measurement.filename for measurement in measurements)


class MovedFile(object):
    """The silly thing is that the parsers sometimes do checks on the
    format of filenames, and then lizard-progress saves the files with
    a timestamp added to the front, making the tests always fail if
    they are repeated later.

    We need to run the repeated tests on a version of the file that
    has the untimestamped name. We put it in /tmp and use this context
    manager to ensure that it is deleted afterwards."""

    def __init__(self, path):
        self.path = path

    def __enter__(self):
        self.new_path = os.path.join(
            '/tmp',
            orig_from_unique_filename(os.path.basename(self.path)))
        shutil.copy(self.path, self.new_path)

        return self.new_path

    def __exit__(self, _exc_type, _exc_value, _traceback):
        os.remove(self.new_path)


def check_uploaded_files(project, contractor):
    """Iterate over all files, get parsers for them, try the parsers
    on the files.

    Returned is a list of errors, in the form of 3-tuples
    (current-file-path, original-filename, error-message)."""

    files = current_files(all_measurements(project, contractor))
    specifics = project.specifics()

    errors = []

    for path in files:
        with MovedFile(path) as moved_file:
            filename = os.path.basename(moved_file)
            parsers = specifics.parsers(filename)

            for parser in parsers:
                parse_object = parser_factory(
                    parser, project, contractor, moved_file)
                result = parse_object.parse(check_only=True)

                if result.success:
                    # Skip other parsers
                    break
                elif not result.error:
                    # Unsuccessful but no errors, parser not suited
                    continue
                else:
                    errors.append((path, filename, result.error))
                    break
            else:
                errors.append((path, filename, "No suitable parser found."))

    return errors


class Command(BaseCommand):
    """Command that goes through all uploaded data and re-checks it."""

    args = "<projectslug> <contractorslug>"
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
        errors = check_uploaded_files(self.project, self.contractor)

        for _path, original_filename, error in errors:
            self.stdout.write("%s: %s\n" % (original_filename, error))

    def check_arguments(self, args):
        """Check the arguments. Errors write some information to
        stderr, then raise CommandError with the actual error."""

        if len(args) > 2:
            self.stderr.write("Arguments: %s.\n" % (self.args,))
            raise CommandError("Too many arguments.")

        if not args:
            self.stderr.write("Arguments: %s.\n" % (self.args,))
            projects = models.Project.objects.all()
            if projects:
                self.stderr.write("Available projects:\n")
                for project in projects:
                    self.stderr.write("- %s\n" % (project.slug,))
            raise CommandError("No project slug given.")

        try:
            self.project = models.Project.objects.get(slug=args[0])
        except models.Project.DoesNotExist:
            raise CommandError("Project '%s' does not exist." % (args[0],))

        if len(args) == 1:
            self.stderr.write("Arguments: %s.\n" % (self.args,))
            contractors = models.Contractor.objects.filter(
                project=self.project).all()
            if contractors:
                self.stderr.write("Available contractors for project %s:\n" %
                                  (self.project.slug,))
                for contractor in contractors:
                    self.stderr.write("- %s\n" % (contractor.slug,))
            raise CommandError("No contractor slug given.")

        try:
            self.contractor = models.Contractor.objects.get(
                project=self.project, slug=args[1])
        except models.Contractor.DoesNotExist:
            raise CommandError("Contractor '%s' does not exist." % (args[1],))
