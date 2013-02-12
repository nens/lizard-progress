# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Project'
        db.create_table('lizard_progress_project', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=50)),
            ('slug', self.gf('django.db.models.fields.SlugField')(unique=True, max_length=50)),
            ('superuser', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True, blank=True)),
        ))
        db.send_create_signal('lizard_progress', ['Project'])

        # Adding model 'Contractor'
        db.create_table('lizard_progress_contractor', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lizard_progress.Project'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=50)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True, blank=True)),
        ))
        db.send_create_signal('lizard_progress', ['Contractor'])

        # Adding unique constraint on 'Contractor', fields ['project', 'slug']
        db.create_unique('lizard_progress_contractor', ['project_id', 'slug'])

        # Adding model 'Area'
        db.create_table('lizard_progress_area', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lizard_progress.Project'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('slug', self.gf('django.db.models.fields.CharField')(max_length=50)),
        ))
        db.send_create_signal('lizard_progress', ['Area'])

        # Adding model 'Location'
        db.create_table('lizard_progress_location', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('location_code', self.gf('django.db.models.fields.CharField')(max_length=50, db_index=True)),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lizard_progress.Project'])),
            ('area', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lizard_progress.Area'], null=True, blank=True)),
            ('the_geom', self.gf('django.contrib.gis.db.models.fields.PointField')(srid=28992, null=True)),
            ('information', self.gf('jsonfield.fields.JSONField')(null=True, blank=True)),
        ))
        db.send_create_signal('lizard_progress', ['Location'])

        # Adding unique constraint on 'Location', fields ['location_code', 'project']
        db.create_unique('lizard_progress_location', ['location_code', 'project_id'])

        # Adding model 'AvailableMeasurementType'
        db.create_table('lizard_progress_availablemeasurementtype', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=50)),
            ('slug', self.gf('django.db.models.fields.SlugField')(unique=True, max_length=50)),
            ('default_icon_missing', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('default_icon_complete', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('can_be_displayed', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('needs_predefined_locations', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('needs_scheduled_measurements', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('description', self.gf('django.db.models.fields.TextField')(default='', blank=True)),
        ))
        db.send_create_signal('lizard_progress', ['AvailableMeasurementType'])

        # Adding model 'MeasurementType'
        db.create_table('lizard_progress_measurementtype', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('mtype', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lizard_progress.AvailableMeasurementType'])),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lizard_progress.Project'])),
            ('icon_missing', self.gf('django.db.models.fields.CharField')(max_length=50, null=True, blank=True)),
            ('icon_complete', self.gf('django.db.models.fields.CharField')(max_length=50, null=True, blank=True)),
        ))
        db.send_create_signal('lizard_progress', ['MeasurementType'])

        # Adding unique constraint on 'MeasurementType', fields ['project', 'mtype']
        db.create_unique('lizard_progress_measurementtype', ['project_id', 'mtype_id'])

        # Adding model 'ScheduledMeasurement'
        db.create_table('lizard_progress_scheduledmeasurement', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lizard_progress.Project'])),
            ('contractor', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lizard_progress.Contractor'])),
            ('measurement_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lizard_progress.MeasurementType'])),
            ('location', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lizard_progress.Location'])),
            ('timestamp', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('complete', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('lizard_progress', ['ScheduledMeasurement'])

        # Adding unique constraint on 'ScheduledMeasurement', fields ['project', 'contractor', 'measurement_type', 'location']
        db.create_unique('lizard_progress_scheduledmeasurement', ['project_id', 'contractor_id', 'measurement_type_id', 'location_id'])

        # Adding model 'Measurement'
        db.create_table('lizard_progress_measurement', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('scheduled', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lizard_progress.ScheduledMeasurement'])),
            ('data', self.gf('jsonfield.fields.JSONField')(null=True)),
            ('date', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('the_geom', self.gf('django.contrib.gis.db.models.fields.PointField')(srid=28992, null=True, blank=True)),
            ('filename', self.gf('django.db.models.fields.CharField')(max_length=1000)),
            ('timestamp', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
        ))
        db.send_create_signal('lizard_progress', ['Measurement'])

        # Adding model 'Hydrovak'
        db.create_table('lizard_progress_hydrovak', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lizard_progress.Project'])),
            ('br_ident', self.gf('django.db.models.fields.CharField')(max_length=24)),
            ('the_geom', self.gf('django.contrib.gis.db.models.fields.LineStringField')(srid=28992)),
        ))
        db.send_create_signal('lizard_progress', ['Hydrovak'])

        # Adding unique constraint on 'Hydrovak', fields ['project', 'br_ident']
        db.create_unique('lizard_progress_hydrovak', ['project_id', 'br_ident'])


    def backwards(self, orm):
        # Removing unique constraint on 'Hydrovak', fields ['project', 'br_ident']
        db.delete_unique('lizard_progress_hydrovak', ['project_id', 'br_ident'])

        # Removing unique constraint on 'ScheduledMeasurement', fields ['project', 'contractor', 'measurement_type', 'location']
        db.delete_unique('lizard_progress_scheduledmeasurement', ['project_id', 'contractor_id', 'measurement_type_id', 'location_id'])

        # Removing unique constraint on 'MeasurementType', fields ['project', 'mtype']
        db.delete_unique('lizard_progress_measurementtype', ['project_id', 'mtype_id'])

        # Removing unique constraint on 'Location', fields ['location_code', 'project']
        db.delete_unique('lizard_progress_location', ['location_code', 'project_id'])

        # Removing unique constraint on 'Contractor', fields ['project', 'slug']
        db.delete_unique('lizard_progress_contractor', ['project_id', 'slug'])

        # Deleting model 'Project'
        db.delete_table('lizard_progress_project')

        # Deleting model 'Contractor'
        db.delete_table('lizard_progress_contractor')

        # Deleting model 'Area'
        db.delete_table('lizard_progress_area')

        # Deleting model 'Location'
        db.delete_table('lizard_progress_location')

        # Deleting model 'AvailableMeasurementType'
        db.delete_table('lizard_progress_availablemeasurementtype')

        # Deleting model 'MeasurementType'
        db.delete_table('lizard_progress_measurementtype')

        # Deleting model 'ScheduledMeasurement'
        db.delete_table('lizard_progress_scheduledmeasurement')

        # Deleting model 'Measurement'
        db.delete_table('lizard_progress_measurement')

        # Deleting model 'Hydrovak'
        db.delete_table('lizard_progress_hydrovak')


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
            'description': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'}),
            'needs_predefined_locations': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'needs_scheduled_measurements': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50'})
        },
        'lizard_progress.contractor': {
            'Meta': {'unique_together': "(('project', 'slug'),)", 'object_name': 'Contractor'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lizard_progress.Project']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        'lizard_progress.hydrovak': {
            'Meta': {'unique_together': "(('project', 'br_ident'),)", 'object_name': 'Hydrovak'},
            'br_ident': ('django.db.models.fields.CharField', [], {'max_length': '24'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lizard_progress.Project']"}),
            'the_geom': ('django.contrib.gis.db.models.fields.LineStringField', [], {'srid': '28992'})
        },
        'lizard_progress.location': {
            'Meta': {'unique_together': "(('location_code', 'project'),)", 'object_name': 'Location'},
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
            'Meta': {'unique_together': "(('project', 'mtype'),)", 'object_name': 'MeasurementType'},
            'icon_complete': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'icon_missing': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mtype': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lizard_progress.AvailableMeasurementType']"}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lizard_progress.Project']"})
        },
        'lizard_progress.project': {
            'Meta': {'object_name': 'Project'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50'}),
            'superuser': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        'lizard_progress.scheduledmeasurement': {
            'Meta': {'unique_together': "(('project', 'contractor', 'measurement_type', 'location'),)", 'object_name': 'ScheduledMeasurement'},
            'complete': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'contractor': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lizard_progress.Contractor']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lizard_progress.Location']"}),
            'measurement_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lizard_progress.MeasurementType']"}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lizard_progress.Project']"}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['lizard_progress']