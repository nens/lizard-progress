# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'NotificationType'
        db.create_table(u'email_notifications_notificationtype', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=255)),
            ('subject_template', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('body_template', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal(u'email_notifications', ['NotificationType'])

        # Adding model 'Notification'
        db.create_table(u'email_notifications_notification', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('notification_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['email_notifications.NotificationType'])),
            ('recipient', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('actor', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('action_object', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('target', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('extra', self.gf('jsonfield.fields.JSONField')(null=True, blank=True)),
            ('emailed', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('emailed_on', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'email_notifications', ['Notification'])

        # Adding model 'NotificationSubscription'
        db.create_table(u'email_notifications_notificationsubscription', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('notification_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['email_notifications.NotificationType'])),
            ('subscriber_content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'])),
            ('subscriber_object_id', self.gf('django.db.models.fields.PositiveIntegerField')()),
        ))
        db.send_create_signal(u'email_notifications', ['NotificationSubscription'])


    def backwards(self, orm):
        # Deleting model 'NotificationType'
        db.delete_table(u'email_notifications_notificationtype')

        # Deleting model 'Notification'
        db.delete_table(u'email_notifications_notification')

        # Deleting model 'NotificationSubscription'
        db.delete_table(u'email_notifications_notificationsubscription')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'email_notifications.notification': {
            'Meta': {'object_name': 'Notification'},
            'action_object': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'actor': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'emailed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'emailed_on': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'extra': ('jsonfield.fields.JSONField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'notification_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['email_notifications.NotificationType']"}),
            'recipient': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'target': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'})
        },
        u'email_notifications.notificationsubscription': {
            'Meta': {'object_name': 'NotificationSubscription'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'notification_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['email_notifications.NotificationType']"}),
            'subscriber_content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            'subscriber_object_id': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        u'email_notifications.notificationtype': {
            'Meta': {'object_name': 'NotificationType'},
            'body_template': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'subject_template': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['email_notifications']