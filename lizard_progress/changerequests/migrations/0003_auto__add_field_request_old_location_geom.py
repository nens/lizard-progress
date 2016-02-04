# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Request.old_location_geom'
        db.add_column(u'changerequests_request', 'old_location_geom',
                      self.gf('django.contrib.gis.db.models.fields.PointField')(srid=28992, null=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Request.old_location_geom'
        db.delete_column(u'changerequests_request', 'old_location_geom')


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
        u'changerequests.points': {
            'Meta': {'object_name': 'Points'},
            'dx': ('django.db.models.fields.IntegerField', [], {}),
            'dy': ('django.db.models.fields.IntegerField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location_code': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'the_geom': ('django.contrib.gis.db.models.fields.PointField', [], {'srid': '28992'})
        },
        u'changerequests.possiblerequest': {
            'Meta': {'ordering': "(u'location_code',)", 'object_name': 'PossibleRequest'},
            'accepted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location_code': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'request_type': ('django.db.models.fields.IntegerField', [], {}),
            'requested': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'the_geom': ('django.contrib.gis.db.models.fields.PointField', [], {'srid': '28992', 'null': 'True'}),
            'uploaded_file': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['lizard_progress.UploadedFile']"})
        },
        u'changerequests.request': {
            'Meta': {'ordering': "(u'creation_date',)", 'object_name': 'Request'},
            'activity': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['lizard_progress.Activity']", 'null': 'True'}),
            'change_date': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'created_by_manager': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invalid_reason': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'location_code': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'motivation': ('django.db.models.fields.TextField', [], {}),
            'motivation_changed': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'old_location_code': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'old_location_geom': ('django.contrib.gis.db.models.fields.PointField', [], {'srid': '28992', 'null': 'True'}),
            'possible_request': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['changerequests.PossibleRequest']", 'null': 'True', 'on_delete': 'models.SET_NULL', 'blank': 'True'}),
            'refusal_reason': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'request_status': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'request_type': ('django.db.models.fields.IntegerField', [], {}),
            'seen': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'the_geom': ('django.contrib.gis.db.models.fields.PointField', [], {'srid': '28992', 'null': 'True'})
        },
        u'changerequests.requestcomment': {
            'Meta': {'ordering': "(u'comment_time',)", 'object_name': 'RequestComment'},
            'comment': ('django.db.models.fields.TextField', [], {}),
            'comment_time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'request': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['changerequests.Request']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'lizard_progress.activity': {
            'Meta': {'object_name': 'Activity'},
            'contractor': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['lizard_progress.Organization']", 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'measurement_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['lizard_progress.AvailableMeasurementType']", 'null': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'default': "u'Activity name'", 'max_length': '100'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['lizard_progress.Project']"}),
            'source_activity': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['lizard_progress.Activity']", 'null': 'True', 'blank': 'True'})
        },
        u'lizard_progress.availablemeasurementtype': {
            'Meta': {'ordering': "(u'name',)", 'object_name': 'AvailableMeasurementType'},
            'can_be_displayed': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'default_icon_complete': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'default_icon_missing': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'delete_on_archive': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "u''", 'blank': 'True'}),
            'has_only_point_locations': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'implementation': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'keep_updated_measurements': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'likes_predefined_locations': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'}),
            'needs_predefined_locations': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'needs_scheduled_measurements': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50'})
        },
        u'lizard_progress.errormessage': {
            'Meta': {'object_name': 'ErrorMessage'},
            'error_code': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'error_message': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'lizard_progress.lizardconfiguration': {
            'Meta': {'object_name': 'LizardConfiguration'},
            'geoserver_database_engine': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            'geoserver_table_name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'upload_config': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            'upload_url_template': ('django.db.models.fields.CharField', [], {'max_length': '300'})
        },
        u'lizard_progress.measurementtypeallowed': {
            'Meta': {'object_name': 'MeasurementTypeAllowed'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mtype': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['lizard_progress.AvailableMeasurementType']"}),
            'organization': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['lizard_progress.Organization']"}),
            'visible': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        },
        u'lizard_progress.organization': {
            'Meta': {'ordering': "(u'name',)", 'object_name': 'Organization'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'errors': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['lizard_progress.ErrorMessage']", 'symmetrical': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_project_owner': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'lizard_config': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['lizard_progress.LizardConfiguration']", 'null': 'True', 'blank': 'True'}),
            'mtypes_allowed': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['lizard_progress.AvailableMeasurementType']", 'through': u"orm['lizard_progress.MeasurementTypeAllowed']", 'symmetrical': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        u'lizard_progress.project': {
            'Meta': {'ordering': "(u'name',)", 'unique_together': "[(u'name', u'organization')]", 'object_name': 'Project'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_archived': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'organization': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['lizard_progress.Organization']"}),
            'project_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['lizard_progress.ProjectType']", 'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '60'})
        },
        u'lizard_progress.projecttype': {
            'Meta': {'unique_together': "((u'name', u'organization'),)", 'object_name': 'ProjectType'},
            'default': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'organization': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['lizard_progress.Organization']"}),
            'show_numbers_on_map': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        u'lizard_progress.uploadedfile': {
            'Meta': {'object_name': 'UploadedFile'},
            'activity': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['lizard_progress.Activity']", 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'linelike': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'path': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'ready': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'success': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {}),
            'uploaded_by': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        }
    }

    complete_apps = ['changerequests']