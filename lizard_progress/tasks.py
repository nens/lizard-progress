"""Contains Celery tasks."""

# Python 3 is coming
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from celery.task import task

from lizard_progress import archive
from lizard_progress import process_uploaded_file
from lizard_progress import exports
from lizard_progress.util import shapevac

import logging
logger = logging.getLogger(__name__)


@task
def add(x, y):
    """Add two numbers, useful in testing."""
    return x + y


@task
def process_uploaded_file_task(uploaded_file_id):
    """Call the process_uploaded_file function."""
    import sys
    sys.stdout.write('process uploaded file task \n')
    sys.stdout.flush()
    try:
        process_uploaded_file.process_uploaded_file(uploaded_file_id)
    except:
        logger.exception("Error in task 'process_uploaded_file_task'.")
        raise


@task
def start_export_run(export_run_id, user):
    """Start the given export run."""
    try:
        exports.start_run(export_run_id, user)
    except:
        logger.exception("Error in task 'start_export_run'.")
        raise


@task
def shapefile_vacuum(directory):
    """Put shapefile parts into zip files in directory."""
    try:
        shapevac.shapefile_vacuum_directory(directory)
    except:
        logger.exception("Error in task 'shapefile_vacuum'.")
        raise


@task
def archive_task(project_id):
    """Call the archive function."""
    try:
        archive.archive(project_id)
    except:
        logger.exception("Error in task 'archive_task'.")
        raise
