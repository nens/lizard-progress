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

        for measurement in models.Measurement.objects.all():
            activity = measurement.location.activity

            dirname, filename = os.path.split(measurement.filename)

            if (dirname == directories.upload_dir(activity) and
                    filename.count('-') >= 3):
                # This is the kind of filename we want to fix.
                new_filename = filename.split('-')[3:]
                new_path = process_uploaded_file(activity, new_filename)

                # Move and record new path
                shutil.move(measurement.filename, new_path)
                measurement.filename = new_path
                measurement.save()
