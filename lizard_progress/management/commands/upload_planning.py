# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

"""Upload (ribx) planning.

This command is typically used if the file is too large to be uploaded
via the site.

NOTE: shapefile not supported at the moment, only ribx.
"""

# Python 3 is coming
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from django.core.management.base import BaseCommand, CommandError
from lizard_progress import models
from lizard_progress.views.activity import PlanningView


class Command(BaseCommand):
    args = "<activity id AKA primary key> <filepath>"
    help = "Upload planning from file for an activity."

    def handle(self, *args, **options):
        try:
            activity_id, ribxpath = args
        except ValueError:
            raise CommandError("Number of arguments incorrect.")

        activity = models.Activity.objects.get(pk=int(activity_id))

        locations_from_ribx = dict(
            PlanningView.get_locations_from_ribx(ribxpath, activity))

        if locations_from_ribx:
            existing_measurements = list(
                models.Measurement.objects.filter(
                    location__activity=activity
                ).select_related("location")
            )

            PlanningView.process_ribx_locations(
                activity, locations_from_ribx, ribxpath, existing_measurements)
