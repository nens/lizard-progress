"""Contains Celery tasks."""

# Python 3 is coming
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from celery.task import task


@task
def send_notification(notification):
    notification.send()
