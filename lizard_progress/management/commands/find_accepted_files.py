# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

"""Find uploaded files that haven't got an AcceptedFile object yet"""

# Python 3 is coming
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import glob
import logging
import os

from django.core.management.base import BaseCommand
from lizard_progress.models import AcceptedFile
from lizard_progress.models import Activity
from lizard_progress.util.directories import BASE_DIR

logger = logging.getLogger(__name__)


def id_from_path(path):
    id = path.split('/')[2]
    try:
        return int(id)
    except ValueError:
        logger.warn("Non-int activity id %s for %s", id, path)


class Command(BaseCommand):
    args = ""
    help = "Find uploaded files that haven't got an AcceptedFile object yet"

    def handle(self, *args, **options):
        os.chdir(BASE_DIR)
        rel_paths_on_fs = (glob.glob('*/*/*/uploads/*/*') +
                           glob.glob('*/*/*/*/*'))
        rel_paths_on_fs = [path for path in rel_paths_on_fs
                           if os.path.isfile(path)]
        # Perhaps 'final_results' needs to be excluded.
        logger.debug("Found %s uploaded files in %s",
                     len(rel_paths_on_fs), BASE_DIR)
        # Activity ID is the third item in the path.
        on_filesystem = set([(id_from_path(rel_path), rel_path)
                             for rel_path in rel_paths_on_fs
                             if id_from_path(rel_path)])
        in_db = set(AcceptedFile.objects.all().values_list(
            'activity', 'rel_file_path'))

        missing_in_db = on_filesystem - in_db
        erroneously_in_db = in_db - on_filesystem
        logger.info("%s to be added as AcceptedFile, %s to be removed",
                    len(missing_in_db), len(erroneously_in_db))

        activity_ids = Activity.objects.all().values_list('id', flat=True)
        for (activity_id, rel_file_path) in missing_in_db:
            if activity_id not in activity_ids:
                logger.warn("Activity with id %s doesn't exist, skipping %s",
                            activity_id, rel_file_path)
                continue
            activity = Activity.objects.get(pk=activity_id)
            AcceptedFile.create_from_path(activity, rel_file_path)
            logger.debug("Created AcceptedFile for activity %s and file %s",
                         activity_id, rel_file_path)

        for (activity_id, rel_file_path) in erroneously_in_db:
            activity = Activity.objects.get(pk=activity_id)
            AcceptedFile.objects.get(activity=activity,
                                     rel_file_path=rel_file_path).delete()
            logger.info("Deleted AcceptedFile for activity %s and file %s",
                         activity_id, rel_file_path)
