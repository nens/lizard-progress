# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'PossibleRequest'
        db.create_table('changerequests_possiblerequest', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('uploaded_file', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lizard_progress.UploadedFile'])),
            ('mtype', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lizard_progress.AvailableMeasurementType'])),
            ('request_type', self.gf('django.db.models.fields.IntegerField')()),
            ('location_code', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('the_geom', self.gf('django.contrib.gis.db.models.fields.PointField')(srid=28992, null=True)),
        ))
        db.send_create_signal('changerequests', ['PossibleRequest'])


    def backwards(self, orm):
        # Deleting model 'PossibleRequest'
        db.delete_table('changerequests_possiblerequest')


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
        'changerequests.possiblerequest': {
            'Meta': {'object_name': 'PossibleRequest'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location_code': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'mtype': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lizard_progress.AvailableMeasurementType']"}),
            'request_type': ('django.db.models.fields.IntegerField', [], {}),
            'the_geom': ('django.contrib.gis.db.models.fields.PointField', [], {'srid': '28992', 'null': 'True'}),
            'uploaded_file': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lizard_progress.UploadedFile']"})
        },
        'changerequests.request': {
            'Meta': {'ordering': "(u'creation_date',)", 'object_name': 'Request'},
            'change_date': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'contractor': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lizard_progress.Contractor']"}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invalid_reason': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'location_code': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'motivation': ('django.db.models.fields.TextField', [], {}),
            'motivation_changed': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'mtype': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lizard_progress.AvailableMeasurementType']"}),
            'old_location_code': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'refusal_reason': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'request_status': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'request_type': ('django.db.models.fields.IntegerField', [], {}),
            'seen': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'the_geom': ('django.contrib.gis.db.models.fields.PointField', [], {'srid': '28992', 'null': 'True'})
        },
        'changerequests.requestcomment': {
            'Meta': {'ordering': "(u'comment_time',)", 'object_name': 'RequestComment'},
            'comment': ('django.db.models.fields.TextField', [], {}),
            'comment_time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'request': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['changerequests.Request']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
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
        'lizard_progress.lizardconfiguration': {
            'Meta': {'object_name': 'LizardConfiguration'},
            'geoserver_database_engine': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            'geoserver_table_name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'upload_config': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            'upload_url_template': ('django.db.models.fields.CharField', [], {'max_length': '300'})
        },
        'lizard_progress.organization': {
            'Meta': {'object_name': 'Organization'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'errors': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['lizard_progress.ErrorMessage']", 'symmetrical': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_project_owner': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'lizard_config': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lizard_progress.LizardConfiguration']", 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        'lizard_progress.project': {
            'Meta': {'ordering': "(u'name',)", 'object_name': 'Project'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_archived': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'}),
            'organization': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lizard_progress.Organization']"}),
            'project_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lizard_progress.ProjectType']", 'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50'}),
            'superuser': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        'lizard_progress.projecttype': {
            'Meta': {'unique_together': "((u'name', u'organization'),)", 'object_name': 'ProjectType'},
            'default': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'organization': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lizard_progress.Organization']"})
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
        }
    }

    complete_apps = ['changerequests']