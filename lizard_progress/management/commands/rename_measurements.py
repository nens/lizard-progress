# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

"""Command that goes through all the measurements, checks to see if
the file name has the old format (YYMMDD-HHMMSS-0-filename in upload
dir) and if so, renames it to the new style path as given in
path_for_uploaded_file in process_uploaded_file.py.

"""

# Python 3 is coming
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import os
import shutil

from django.core.management.base import BaseCommand

from lizard_progress.util import directories
from lizard_progress import models
from lizard_progress import process_uploaded_file


class Command(BaseCommand):
    """Command that goes through all measurements and updates paths."""

    def handle(self, *args, **options):
        """Run the command."""

        all_filenames = models.Measurement.objects.order_by(
            'filename').distinct('filename').values_list('filename', flat=True)

        for path in all_filenames:
            dirname, filename = os.path.split(path)
            if filename.count('-') < 3:
                # Skip
                continue

            measurements = list(models.Measurement.objects.filter(
                filename=path).select_related())

            activity = measurements[0].location.activity

            if (dirname == directories.upload_dir(activity)):
                # This is the kind of filename we want to fix.
                new_filename = filename.split('-', 3)[-1]
                new_path = process_uploaded_file.path_for_uploaded_file(
                    activity, new_filename)

                print("{} -> {}".format(path, new_path))

                # Move and record new path
                if os.path.exists(path):
                    shutil.move(path, new_path)

                for measurement in measurements:
                    measurement.filename = new_path
                    measurement.save()
