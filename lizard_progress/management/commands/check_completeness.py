# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

"""Check and set completeness.  """

# Python 3 is coming
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import traceback

from django.core.management.base import BaseCommand, CommandError
from django.db.models import ObjectDoesNotExist

from lizard_progress import models


class Command(BaseCommand):
    args = "<organization slug> <project slug> <activity name>"
    help = "Check and set completeness."

    def handle(self, *args, **options):
        try:
            organization_name, project_slug, activity_name = args[0:3]
        except ValueError:
            raise CommandError("Not enough arguments.")
        try:
            # Get activity we want to inspect
            organization = models.Organization.objects.get(
                name=organization_name)
            project = models.Project.objects.get(
                organization=organization, slug=project_slug)
            activity = models.Activity.objects.get(
                project=project, name=activity_name)
        except ObjectDoesNotExist:
            raise CommandError(
                "Please provide a valid organization, project and activity. "
                "Msg: %s" % traceback.format_exc())

        print("---\nStarting checks for activity %s..." % activity)
        locations_to_fix = []
        for location in activity.location_set.all():
            complete_pre = location.complete
            complete_checked = location.check_completeness()
            if complete_pre != complete_checked:
                print(
                    "Difference in completeness for location: %s. "
                    "location.complete = %s, actual completeness = %s " %
                    (location, complete_pre, complete_checked))
                locations_to_fix.append(location)
        if locations_to_fix:
            answer = raw_input(
                "%s completeness errors were found. Fix locations? [y/N] " %
                len(locations_to_fix))
            if answer and answer.lower()[0] == 'y':
                print("Start fixing completeness.")
                for loc in locations_to_fix:
                    print("Fixing %s" % loc)
                    loc.set_completeness()
            else:
                print("No fixes will be performed.")
        else:
            print("No completeness errors were found.")
        print("Completeness check finished.\n---")

        # missing = []
        # if location.measurement_set.count() == 0:
        #     all_uploaded = complete_pre
        # else:
        #     all_uploaded = True
        #     for measurement in location.measurement_set.all():
        #         all_uploaded = all_uploaded and \
        #             not measurement.missing_attachments().exists()
        #         missing.extend(measurement.missing_attachments())
        # if complete_pre != all_uploaded:
        #     print(
        #         "Difference in location.complete (=%s) and the missing "
        #         "attachments (=%s) for location %s. Missing are: %s" %
        #         (complete_pre, all_uploaded, location, missing))
        #     # import pdb; pdb.set_trace()
