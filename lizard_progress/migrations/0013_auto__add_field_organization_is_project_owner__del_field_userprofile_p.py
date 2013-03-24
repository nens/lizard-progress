# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Organization.is_project_owner'
        db.add_column('lizard_progress_organization', 'is_project_owner',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)

        # Deleting field 'UserProfile.profiletype'
        db.delete_column('lizard_progress_userprofile', 'profiletype')


    def backwards(self, orm):
        # Deleting field 'Organization.is_project_owner'
        db.delete_column('lizard_progress_organization', 'is_project_owner')

        # Adding field 'UserProfile.profiletype'
        db.add_column('lizard_progress_userprofile', 'profiletype',
                      self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True),
                      keep_default=False)


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'lizard_progress.area': {
            'Meta': {'object_name': 'Area'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lizard_progress.Project']"}),
            'slug': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'lizard_progress.availablemeasurementtype': {
            'Meta': {'object_name': 'AvailableMeasurementType'},
            'can_be_displayed': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'default_icon_complete': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'default_icon_missing': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "u''", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'likes_predefined_locations': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'}),
            'needs_predefined_locations': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'needs_scheduled_measurements': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50'})
        },
        'lizard_progress.contractor': {
            'Meta': {'unique_together': "((u'project', u'organization'),)", 'object_name': 'Contractor'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'organization': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lizard_progress.Organization']", 'null': 'True', 'blank': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lizard_progress.Project']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'})
        },
        'lizard_progress.errormessage': {
            'Meta': {'object_name': 'ErrorMessage'},
            'error_code': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'error_message': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'lizard_progress.exportrun': {
            'Meta': {'unique_together': "((u'project', u'contractor', u'measurement_type', u'exporttype'),)", 'object_name': 'ExportRun'},
            'contractor': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lizard_progress.Contractor']"}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'export_running': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'exporttype': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'file_path': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '300', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'measurement_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lizard_progress.AvailableMeasurementType']"}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lizard_progress.Project']"}),
            'ready_for_download': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'lizard_progress.hydrovak': {
            'Meta': {'unique_together': "((u'project', u'br_ident'),)", 'object_name': 'Hydrovak'},
            'br_ident': ('django.db.models.fields.CharField', [], {'max_length': '24'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lizard_progress.Project']"}),
            'the_geom': ('django.contrib.gis.db.models.fields.LineStringField', [], {'srid': '28992'})
        },
        'lizard_progress.location': {
            'Meta': {'unique_together': "((u'location_code', u'project'),)", 'object_name': 'Location'},
            'area': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lizard_progress.Area']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'information': ('jsonfield.fields.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'location_code': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lizard_progress.Project']"}),
            'the_geom': ('django.contrib.gis.db.models.fields.PointField', [], {'srid': '28992', 'null': 'True'})
        },
        'lizard_progress.measurement': {
            'Meta': {'object_name': 'Measurement'},
            'data': ('jsonfield.fields.JSONField', [], {'null': 'True'}),
            'date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'max_length': '1000'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'scheduled': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lizard_progress.ScheduledMeasurement']"}),
            'the_geom': ('django.contrib.gis.db.models.fields.PointField', [], {'srid': '28992', 'null': 'True', 'blank': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'lizard_progress.measurementtype': {
            'Meta': {'unique_together': "((u'project', u'mtype'),)", 'object_name': 'MeasurementType'},
            'icon_complete': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'icon_missing': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mtype': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lizard_progress.AvailableMeasurementType']"}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lizard_progress.Project']"})
        },
        'lizard_progress.organization': {
            'Meta': {'object_name': 'Organization'},
            'allows_non_predefined_locations': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'errors': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['lizard_progress.ErrorMessage']", 'symmetrical': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_project_owner': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        'lizard_progress.project': {
            'Meta': {'object_name': 'Project'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50'}),
            'superuser': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        'lizard_progress.scheduledmeasurement': {
            'Meta': {'unique_together': "((u'project', u'contractor', u'measurement_type', u'location'),)", 'object_name': 'ScheduledMeasurement'},
            'complete': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'contractor': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lizard_progress.Contractor']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lizard_progress.Location']"}),
            'measurement_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lizard_progress.MeasurementType']"}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lizard_progress.Project']"}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'lizard_progress.uploadedfile': {
            'Meta': {'object_name': 'UploadedFile'},
            'contractor': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lizard_progress.Contractor']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'linelike': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'path': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lizard_progress.Project']"}),
            'ready': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'success': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {}),
            'uploaded_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'lizard_progress.uploadedfileerror': {
            'Meta': {'object_name': 'UploadedFileError'},
            'error_code': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'error_message': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'line': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'uploaded_file': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lizard_progress.UploadedFile']"})
        },
        'lizard_progress.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'organization': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lizard_progress.Organization']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'unique': 'True'})
        }
    }

    complete_apps = ['lizard_progress']