# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

"""Check all locations added in the last hour and FIX the completeness"""

# Python 3 is coming
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import datetime
import logging

from django.core.management.base import BaseCommand
from lizard_progress.models import Location

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    args = ""
    help = "Check and set completeness for locations added in the last hour"

    def handle(self, *args, **options):
        hour_ago = datetime.datetime.now() - datetime.timedelta(hours=1)

        for location in Location.objects.filter(timestamp__gt=hour_ago):
            if location.complete != location.check_completeness():
                logger.info("Fixing completeness for location %s",
                            location)
                location.set_completeness()
