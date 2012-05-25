# -*- coding: utf-8 -*-
# Copyright 2011 Nelen & Schuurmans

"""Command that goes through all the uploaded data (most recent
versions only) and runs the parser checks again. This should be used
if the parser checks have changed after some data has been uploaded
already. If the parser hasn't changed, there should be no need."""

import os

from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

from lizard_progress import models
from lizard_progress.specifics import parser_factory
from lizard_progress.models import all_measurements
from lizard_progress.models import current_files
from lizard_progress.tools import MovedFile


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

        for _path, _original_filename, error in errors:
            self.stdout.write("%s\n" % (error,))

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
