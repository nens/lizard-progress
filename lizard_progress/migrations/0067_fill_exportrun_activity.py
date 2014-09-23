# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

class Migration(DataMigration):

    def forwards(self, orm):
        "Write your forwards methods here."
        # Note: Remember to use orm['appname.ModelName'] rather than "from appname.models..."

        for exportrun in orm['lizard_progress.ExportRun'].objects.all():
            try:
                activity = orm['lizard_progress.Activity'].objects.get(
                    project=exportrun.project,
                    contractor=exportrun.organization,
                    measurement_type=exportrun.measurement_type)
            except orm['lizard_progress.Activity'].DoesNotExist:
                continue

            exportrun.activity = activity
            exportrun.save()

    def backwards(self, orm):
        "Write your backwards methods here."

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
        u'lizard_progress.activity': {
            'Meta': {'object_name': 'Activity'},
            'contractor': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['lizard_progress.Organization']", 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'measurement_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['lizard_progress.AvailableMeasurementType']", 'null': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'default': "u'Activity name'", 'max_length': '100'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['lizard_progress.Project']"})
        },
        u'lizard_progress.availablemeasurementtype': {
            'Meta': {'ordering': "(u'name',)", 'object_name': 'AvailableMeasurementType'},
            'can_be_displayed': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'default_icon_complete': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'default_icon_missing': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "u''", 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'implementation': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
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
        u'lizard_progress.exportrun': {
            'Meta': {'unique_together': "((u'project', u'organization', u'measurement_type', u'exporttype'),)", 'object_name': 'ExportRun'},
            'activity': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['lizard_progress.Activity']", 'null': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'error_message': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'export_running': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'exporttype': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'file_path': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '300', 'null': 'True'}),
            'generates_file': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'measurement_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['lizard_progress.AvailableMeasurementType']"}),
            'organization': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['lizard_progress.Organization']", 'null': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['lizard_progress.Project']"}),
            'ready_for_download': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        u'lizard_progress.hydrovak': {
            'Meta': {'unique_together': "((u'project', u'br_ident'),)", 'object_name': 'Hydrovak'},
            'br_ident': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['lizard_progress.Project']"}),
            'the_geom': ('django.contrib.gis.db.models.fields.MultiLineStringField', [], {'srid': '28992'})
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
        u'lizard_progress.location': {
            'Meta': {'unique_together': "((u'location_code', u'activity'),)", 'object_name': 'Location'},
            'activity': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['lizard_progress.Activity']", 'null': 'True'}),
            'complete': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'information': ('jsonfield.fields.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'location_code': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'}),
            'the_geom': ('django.contrib.gis.db.models.fields.PointField', [], {'srid': '28992', 'null': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        u'lizard_progress.measurement': {
            'Meta': {'object_name': 'Measurement'},
            'data': ('jsonfield.fields.JSONField', [], {'null': 'True'}),
            'date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'max_length': '1000'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['lizard_progress.Location']", 'null': 'True'}),
            'the_geom': ('django.contrib.gis.db.models.fields.PointField', [], {'srid': '28992', 'null': 'True', 'blank': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        u'lizard_progress.measurementtypeallowed': {
            'Meta': {'object_name': 'MeasurementTypeAllowed'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mtype': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['lizard_progress.AvailableMeasurementType']"}),
            'organization': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['lizard_progress.Organization']"}),
            'visible': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        },
        u'lizard_progress.organization': {
            'Meta': {'object_name': 'Organization'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'errors': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['lizard_progress.ErrorMessage']", 'symmetrical': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_project_owner': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'lizard_config': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['lizard_progress.LizardConfiguration']", 'null': 'True', 'blank': 'True'}),
            'mtypes_allowed': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['lizard_progress.AvailableMeasurementType']", 'through': u"orm['lizard_progress.MeasurementTypeAllowed']", 'symmetrical': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        u'lizard_progress.organizationconfig': {
            'Meta': {'object_name': 'OrganizationConfig'},
            'config_option': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'organization': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['lizard_progress.Organization']"}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'})
        },
        u'lizard_progress.project': {
            'Meta': {'ordering': "(u'name',)", 'unique_together': "[(u'name', u'organization')]", 'object_name': 'Project'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_archived': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'organization': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['lizard_progress.Organization']"}),
            'project_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['lizard_progress.ProjectType']", 'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50'})
        },
        u'lizard_progress.projectconfig': {
            'Meta': {'object_name': 'ProjectConfig'},
            'config_option': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['lizard_progress.Project']"}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True'})
        },
        u'lizard_progress.projecttype': {
            'Meta': {'unique_together': "((u'name', u'organization'),)", 'object_name': 'ProjectType'},
            'default': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'organization': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['lizard_progress.Organization']"})
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
        },
        u'lizard_progress.uploadedfileerror': {
            'Meta': {'object_name': 'UploadedFileError'},
            'error_code': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'error_message': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'line': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'uploaded_file': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['lizard_progress.UploadedFile']"})
        },
        u'lizard_progress.uploadlog': {
            'Meta': {'ordering': "(u'when',)", 'object_name': 'UploadLog'},
            'filename': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mtype': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['lizard_progress.AvailableMeasurementType']"}),
            'num_measurements': ('django.db.models.fields.IntegerField', [], {}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['lizard_progress.Project']"}),
            'uploading_organization': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['lizard_progress.Organization']"}),
            'when': ('django.db.models.fields.DateTimeField', [], {})
        },
        u'lizard_progress.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'organization': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['lizard_progress.Organization']"}),
            'roles': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['lizard_progress.UserRole']", 'symmetrical': 'False'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'unique': 'True'})
        },
        u'lizard_progress.userrole': {
            'Meta': {'object_name': 'UserRole'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        }
    }

    complete_apps = ['lizard_progress']
    symmetrical = True
