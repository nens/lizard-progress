# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

class Migration(DataMigration):

    def forwards(self, orm):
        "Write your forwards methods here."
        orm['lizard_progress.AvailableMeasurementType'].objects.create(
            name='Inmeten dwarsprofiel watergang',
            slug='dwarsprofiel',
            default_icon_missing='bullets/squarered16.png',
            default_icon_complete='bullets/squaregreen16.png',
            can_be_displayed=True,
            needs_predefined_locations=True,
            needs_scheduled_measurements=True,
            description="""De opdrachtnemer meet, op een door HDSR aangegeven locatie, dwarsprofielen in. De output van de opdrachtnemer wordt in de vorm van een .MET-file ge&uuml;pload in de HDSR Upload Server.""")

        orm['lizard_progress.AvailableMeasurementType'].objects.create(
            name="Nemen oeverfoto's",
            slug='oeverfoto',
            default_icon_missing='camera_missing.png',
            default_icon_complete='camera_present.png',
            can_be_displayed=True,
            needs_predefined_locations=True,
            needs_scheduled_measurements=True,
            description="""De opdrachtnemer fotografeert, op een door HDSR aangegeven locatie en bestandsnaam, beide zijden van de watergang (twee oevers). De output van de opdrachtnemer wordt in de vorm van twee .JPG-files (2 foto’s) ge&uuml;pload in de HDSR Upload Server.""")

        orm['lizard_progress.AvailableMeasurementType'].objects.create(
            name='Opgegeven oeverkenmerk',
            slug='oeverkenmerk',
            default_icon_missing='bullets/trianglered16.png',
            default_icon_complete='bullets/trianglegreen16.png',
            can_be_displayed=True,
            needs_predefined_locations=True,
            needs_scheduled_measurements=True,
            description="""De opdrachtnemer beschrijft, voor een door HDSR aangegeven locatie, voor beide zijden van de watergang de betreffende categorie: traditioneel, natuurvriendelijk of niet-ingericht. De output van de opdrachtnemer wordt in de vorm van een .CSV-file ge&uuml;pload in de HDSR Upload Server.""")

        orm['lizard_progress.AvailableMeasurementType'].objects.create(
            name='Neem foto object',
            slug='foto',
            default_icon_missing='camera_missing.png',
            default_icon_complete='camera_present.png',
            can_be_displayed=True,
            needs_predefined_locations=True,
            needs_scheduled_measurements=True,
            description="""De opdrachtnemer fotografeert, op een door HDSR aangegeven locatie en bestandsnaam, het door HDSR bepaalde object. De output van de opdrachtnemer wordt in de vorm van een .JPG-file (1 foto) ge&uuml;pload in de HDSR Upload Server.""")

        orm['lizard_progress.AvailableMeasurementType'].objects.create(
            name='Inmeten peilschaal',
            slug='meting',
            default_icon_missing='bullets/squarered16.png',
            default_icon_complete='bullets/squaregreen16.png',
            can_be_displayed=True,
            needs_predefined_locations=True,
            needs_scheduled_measurements=True,
            description="""De opdrachtnemer leest af en meet in, het waterniveau (mNAP) bij de door HDSR aangegeven peilschaal. De output van de opdrachtnemer wordt in de vorm van een .CSV-file ge&uuml;pload in de HDSR Upload Server.""")

        orm['lizard_progress.AvailableMeasurementType'].objects.create(
            name='Bepalen kwaliteit waterbodem',
            slug='laboratorium_csv',
            default_icon_missing='bullets/squarered16.png',
            default_icon_complete='bullets/squaregreen16.png',
            can_be_displayed=False,
            needs_predefined_locations=False,
            needs_scheduled_measurements=False,
            description="""De opdrachtnemer bemonstert en analyseert, op een door HDSR aangegeven locatie, de waterbodem. De output van de opdrachtnemer wordt in de vorm van een .CSV-file ge&uuml;pload in de HDSR Upload Server.""")

    def backwards(self, orm):
        "Write your backwards methods here."

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
            'information': ('jsonfield.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'location_code': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lizard_progress.Project']"}),
            'the_geom': ('django.contrib.gis.db.models.fields.PointField', [], {'srid': '28992', 'null': 'True'})
        },
        'lizard_progress.measurement': {
            'Meta': {'object_name': 'Measurement'},
            'data': ('jsonfield.JSONField', [], {'null': 'True'}),
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
    symmetrical = True
