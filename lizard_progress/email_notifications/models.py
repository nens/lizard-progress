# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

"""
Hints

    * Please set DEFAULT_FROM_EMAIL in the settings;

"""

# Python 3 is coming
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from django.conf import settings
from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.template import Context, Template
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
import jsonfield

from .signals import notify

User = get_user_model()


class NotificationType(models.Model):
    name = models.CharField(unique=True, max_length=255)
    subject_template = models.CharField(
        max_length=255,
        help_text=_("""Use Django's templating language.
                    Available variables: actor, action_object, target and
                    the items in extra.""")
    )
    body_template = models.TextField(
        help_text=_("""Use Django's templating language.
                    Available variables: actor, action_object, target and
                    the items in extra.""")
    )

    def __unicode__(self):
        return self.name

    @staticmethod
    def _render_template(template, context):
        t = Template(template)
        c = Context(context)
        return t.render(c)

    def get_subject(self, context):
        return self._render_template(self.subject_template, context)

    def get_body(self, context):
        return self._render_template(self.body_template, context)


class Notification(models.Model):
    notification_type = models.ForeignKey(NotificationType)
    recipient = models.ForeignKey(User)
    actor = models.CharField(blank=True, max_length=255)
    action_object = models.CharField(blank=True, max_length=255)
    target = models.CharField(blank=True, max_length=255)
    extra = jsonfield.JSONField(blank=True, null=True)

    created_on = models.DateTimeField(auto_now_add=True)
    emailed = models.BooleanField(default=False)
    emailed_on = models.DateTimeField(blank=True, null=True)

    def __unicode__(self):
        return "{}, {}".format(self.notification_type, self.action_object)

    def get_context(self):
        """ Return the fields in this model as a dictionary. """
        context = {
            'actor': self.actor,
            'action_object': self.action_object,
            'target': self.target,
        }
        if self.extra:
            context.update(self.extra)
        return context

    def get_body(self):
        return self.notification_type.get_body(self.get_context())

    def get_subject(self):
        return self.notification_type.get_subject(self.get_context())

    @classmethod
    def create_notification(cls,
                            notification_type,
                            recipient,
                            actor=None,
                            action_object=None,
                            target=None,
                            extra=None):
        notification = cls(
            notification_type=notification_type,
            recipient=recipient)
        if actor:
            setattr(notification, 'actor', str(actor))
        if action_object:
            setattr(notification, 'action_object', str(action_object))
        if target:
            setattr(notification, 'target', str(target))
        if extra:
            setattr(notification, 'extra', extra)
        notification.save()
        return notification

    def send_notification(self):
        if not self.recipient.email:
            return False
        try:
            send_mail(
                self.get_subject(),
                self.get_body(),
                getattr(settings, 'DEFAULT_FROM_EMAIL', ''),
                [self.recipient.email, ],
            )
        except Exception, e:
            self.emailed = False
            self.save()
            raise e
        else:
            self.emailed = True
            self.emailed_on = timezone.now()
            self.save()
        return True


class NotificationSubscription(models.Model):
    notification_type = models.ForeignKey(NotificationType)
    subscriber_content_type = models.ForeignKey(ContentType)
    subscriber_object_id = models.PositiveIntegerField()
    subscriber = generic.GenericForeignKey(
        'subscriber_content_type',
        'subscriber_object_id'
    )

    def __unicode__(self):
        return "{}, {}".format(self.notification_type, self.subscriber)


def send_notification(notification_type, recipient, **kwargs):
    actor = kwargs.pop('actor', None)
    action_object = kwargs.pop('action_object', None)
    target = kwargs.pop('target', None)
    extra = kwargs.pop('extra', None)

    n = Notification.create_notification(
        notification_type,
        recipient,
        actor=actor,
        action_object=action_object,
        target=target,
        extra=extra)

    n.send_notification()

notify.connect(
    send_notification,
    dispatch_uid='email_notifications.models.notification')
