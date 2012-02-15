# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Project'
        db.create_table('lizard_progress_project', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('slug', self.gf('django.db.models.fields.SlugField')(unique=True, max_length=50, db_index=True)),
            ('superuser', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True, blank=True)),
        ))
        db.send_create_signal('lizard_progress', ['Project'])

        # Adding model 'Contractor'
        db.create_table('lizard_progress_contractor', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lizard_progress.Project'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=50, db_index=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True, blank=True)),
        ))
        db.send_create_signal('lizard_progress', ['Contractor'])

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
            ('unique_id', self.gf('django.db.models.fields.CharField')(max_length=50, primary_key=True)),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lizard_progress.Project'])),
            ('area', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lizard_progress.Area'], null=True, blank=True)),
            ('the_geom', self.gf('django.contrib.gis.db.models.fields.PointField')(srid=28992, null=True)),
            ('information', self.gf('lizard_map.models.JSONField')(null=True, blank=True)),
        ))
        db.send_create_signal('lizard_progress', ['Location'])

        # Adding unique constraint on 'Location', fields ['unique_id', 'project']
        db.create_unique('lizard_progress_location', ['unique_id', 'project_id'])

        # Adding model 'MeasurementType'
        db.create_table('lizard_progress_measurementtype', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lizard_progress.Project'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=50, db_index=True)),
            ('icon_missing', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('icon_complete', self.gf('django.db.models.fields.CharField')(max_length=50)),
        ))
        db.send_create_signal('lizard_progress', ['MeasurementType'])

        # Adding model 'ScheduledMeasurement'
        db.create_table('lizard_progress_scheduledmeasurement', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lizard_progress.Project'])),
            ('contractor', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lizard_progress.Contractor'])),
            ('measurement_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lizard_progress.MeasurementType'])),
            ('location', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lizard_progress.Location'])),
            ('complete', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('lizard_progress', ['ScheduledMeasurement'])

        # Adding model 'Measurement'
        db.create_table('lizard_progress_measurement', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('scheduled', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lizard_progress.ScheduledMeasurement'])),
            ('data', self.gf('lizard_map.models.JSONField')(null=True)),
            ('date', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('the_geom', self.gf('django.contrib.gis.db.models.fields.PointField')(srid=28992, null=True, blank=True)),
        ))
        db.send_create_signal('lizard_progress', ['Measurement'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'Location', fields ['unique_id', 'project']
        db.delete_unique('lizard_progress_location', ['unique_id', 'project_id'])

        # Deleting model 'Project'
        db.delete_table('lizard_progress_project')

        # Deleting model 'Contractor'
        db.delete_table('lizard_progress_contractor')

        # Deleting model 'Area'
        db.delete_table('lizard_progress_area')

        # Deleting model 'Location'
        db.delete_table('lizard_progress_location')

        # Deleting model 'MeasurementType'
        db.delete_table('lizard_progress_measurementtype')

        # Deleting model 'ScheduledMeasurement'
        db.delete_table('lizard_progress_scheduledmeasurement')

        # Deleting model 'Measurement'
        db.delete_table('lizard_progress_measurement')


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
        'lizard_progress.contractor': {
            'Meta': {'object_name': 'Contractor'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lizard_progress.Project']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        'lizard_progress.location': {
            'Meta': {'unique_together': "(('unique_id', 'project'),)", 'object_name': 'Location'},
            'area': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lizard_progress.Area']", 'null': 'True', 'blank': 'True'}),
            'information': ('lizard_map.models.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lizard_progress.Project']"}),
            'the_geom': ('django.contrib.gis.db.models.fields.PointField', [], {'srid': '28992', 'null': 'True'}),
            'unique_id': ('django.db.models.fields.CharField', [], {'max_length': '50', 'primary_key': 'True'})
        },
        'lizard_progress.measurement': {
            'Meta': {'object_name': 'Measurement'},
            'data': ('lizard_map.models.JSONField', [], {'null': 'True'}),
            'date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'scheduled': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lizard_progress.ScheduledMeasurement']"}),
            'the_geom': ('django.contrib.gis.db.models.fields.PointField', [], {'srid': '28992', 'null': 'True', 'blank': 'True'})
        },
        'lizard_progress.measurementtype': {
            'Meta': {'object_name': 'MeasurementType'},
            'icon_complete': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'icon_missing': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lizard_progress.Project']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'})
        },
        'lizard_progress.project': {
            'Meta': {'object_name': 'Project'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'superuser': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        'lizard_progress.scheduledmeasurement': {
            'Meta': {'object_name': 'ScheduledMeasurement'},
            'complete': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'contractor': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lizard_progress.Contractor']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lizard_progress.Location']"}),
            'measurement_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lizard_progress.MeasurementType']"}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lizard_progress.Project']"})
        }
    }

    complete_apps = ['lizard_progress']
