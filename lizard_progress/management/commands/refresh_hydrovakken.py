# -*- coding: utf-8 -*-
# Copyright 2011 Nelen & Schuurmans

"""Loops over all Hydrovakken shapefiles of all projects, and loads
them all into the database. Each shapefile that is loaded remove all
existing hydrovakken of that project, then reload them from the
shapefile."""

from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

from lizard_progress import models


class Command(BaseCommand):
    """Re-load all Hydrovakken in all projects."""

    args = ""
    help = """Loop over all projects and reload all Hydrovakken."""

    def handle(self, *args, **options):
        """Run the command."""

        errors = False

        for project in models.Project.objects.all():
            print "{}...".format(project)
            error_message = project.refresh_hydrovakken()
            if error_message:
                print "!!" + error_message
                errors = True

        if errors:
            raise CommandError("There were errors.")
