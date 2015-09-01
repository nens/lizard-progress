# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

"""Factories for models in email_notifications."""

# Python 3 is coming
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import factory

from lizard_progress.email_notifications import models


class NotificationTypeF(factory.DjangoModelFactory):
    class Meta:
        model = models.NotificationType

    name = 'testnotification'
    description = 'Just for testing'
    subject_template = '{{ actor }} sends a mail to {{ target }} about {{ action_object }}'
    body_template = '{{ actor }} sends a mail to {{ target }} about {{ action_object }}'
