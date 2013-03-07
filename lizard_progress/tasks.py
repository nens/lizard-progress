"""Contains Celery tasks."""

# Python 3 is coming
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from celery.task import task

from lizard_progress import process_uploaded_file


@task
def add(x, y):
    """Add two numbers, useful in testing."""
    return x + y


@task
def process_uploaded_file_task(uploaded_file_id):
    """Call the process_uploaded_file function."""
    process_uploaded_file.process_uploaded_file(uploaded_file_id)
