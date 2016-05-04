# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

"""Implementation of the Project archive task."""

# Python 3 is coming
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import logging

from .models import Project, Measurement

logger = logging.getLogger(__name__)


def archive(project_id):
    """Archive a project.

    This has a side effect for Projects with measurements with measurement
    types that have the delete_on_archive field set: those measurements
    will be deleted, both in db and on disk. The motivation for this is
    that we want to remove 'attachment' measurement files, e.g., all media
    files belonging to a ribx, but not the ribx itself.
    """
    try:
        project = Project.objects.get(pk=project_id)
    except Project.DoesNotExist:
        logger.warn("project_id not found in task: %s", project_id)
        return
    logger.info("Archiving project %s", project)
    # This query returns all Measurements that (1) belong to a Project,
    # (2) that have a parent Measurement, which entails that it is an
    # attachment (e.g., media files belonging to a Ribx), and (3) have
    # a measurement type that can be deleted.
    measurements = Measurement.objects.filter(
        location__activity__project=project,
        parent__isnull=False,
        location__activity__measurement_type__delete_on_archive=True)
    logger.debug("Deleting measurements: %s", measurements)
    for m in measurements:
        m.delete(notify=False, deleted_by_contractor=False,
                 set_completeness=False)
    project.is_archived = True
    project.save()
