# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

"""Check that mails are actually sent. lizard_progress.testsettings defines
that we use the in-memory backend, see
https://docs.djangoproject.com/en/1.6/topics/email/#in-memory-backend .
"""

# Python 3 is coming
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from django.test import TestCase

from django.core import mail

from lizard_progress.email_notifications import notify

from lizard_progress.tests.test_models import ActivityF
from lizard_progress.tests.test_models import UserF
from lizard_progress.email_notifications.tests.factories import NotificationTypeF  # NoQA


class TestSendingMail(TestCase):
    def test_notify(self):
        activity = ActivityF.create()
        notification_type = NotificationTypeF.create()
        recipient = UserF.create(email='test@example.com')

        notify.send(
            activity,
            notification_type=notification_type,
            recipient=recipient,
            actor='uploader',
            action_object='Also a string',
            target='outbox',
            extra=None)

        self.assertEquals(len(mail.outbox), 1)
