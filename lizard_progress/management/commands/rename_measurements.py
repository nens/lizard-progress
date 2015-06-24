# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

"""Command that goes through all the measurements, checks to see if
the file name has the old format (YYYYMMDD-HHMMSS-0-filename in upload
dir) and if so, renames it to the new style path as given in
path_for_uploaded_file in process_uploaded_file.py.

Note that there was an old bug that placed uploaded files in the wrong
directory (immediately in the activity dir, not in the uploads/
subdirectory), those files are still in the wrong location, this script
fixes that too.

"""

# Python 3 is coming
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import os
import re
import shutil

from django.core.management.base import BaseCommand

from lizard_progress.util import directories
from lizard_progress import models
from lizard_progress import process_uploaded_file

CHARS_TO_REMOVE = len('YYYYMMDD-HHMMSS-0-')


class Command(BaseCommand):
    """Command that goes through all measurements and updates paths."""

    def handle(self, *args, **options):
        """Run the command."""

        all_filenames = models.Measurement.objects.order_by(
            'filename').distinct('filename').values_list('filename', flat=True)

        for path in all_filenames:
            dirname, filename = os.path.split(path)

            if not re.match('\d{8}-\d{6}-\d-', filename):
                # Not in YYYYMMDD-HHMMSS-0- format
                continue

            # All measurements that came out of this file
            measurements = list(models.Measurement.objects.filter(
                filename=path).select_related())

            activity = measurements[0].location.activity

            # Sanity check
            if not dirname.startswith(directories.activity_dir(activity)):
                print("Skipping {}".format(dirname))
                continue

            # Fix the filename.
            new_filename = filename[CHARS_TO_REMOVE:]
            new_path = process_uploaded_file.path_for_uploaded_file(
                activity, new_filename)

            print("{} -> {}".format(path, new_path))

            # Move and record new path
            if os.path.exists(path):
                shutil.move(path, new_path)

            # Update all measurement records that relate to this file
            for measurement in measurements:
                measurement.filename = new_path
                measurement.save()
