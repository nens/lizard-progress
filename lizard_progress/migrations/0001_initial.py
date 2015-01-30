# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'ErrorMessage'
        db.create_table(u'lizard_progress_errormessage', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('error_code', self.gf('django.db.models.fields.CharField')(max_length=30)),
            ('error_message', self.gf('django.db.models.fields.CharField')(max_length=300)),
        ))
        db.send_create_signal(u'lizard_progress', ['ErrorMessage'])

        # Adding model 'Organization'
        db.create_table(u'lizard_progress_organization', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=256, null=True, blank=True)),
            ('is_project_owner', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('lizard_config', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lizard_progress.LizardConfiguration'], null=True, blank=True)),
        ))
        db.send_create_signal(u'lizard_progress', ['Organization'])

        # Adding M2M table for field errors on 'Organization'
        db.create_table(u'lizard_progress_organization_errors', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('organization', models.ForeignKey(orm[u'lizard_progress.organization'], null=False)),
            ('errormessage', models.ForeignKey(orm[u'lizard_progress.errormessage'], null=False))
        ))
        db.create_unique(u'lizard_progress_organization_errors', ['organization_id', 'errormessage_id'])

        # Adding model 'ProjectType'
        db.create_table(u'lizard_progress_projecttype', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('organization', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lizard_progress.Organization'])),
            ('default', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal(u'lizard_progress', ['ProjectType'])

        # Adding unique constraint on 'ProjectType', fields ['name', 'organization']
        db.create_unique(u'lizard_progress_projecttype', ['name', 'organization_id'])

        # Adding model 'UserRole'
        db.create_table(u'lizard_progress_userrole', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('code', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=100)),
        ))
        db.send_create_signal(u'lizard_progress', ['UserRole'])

        # Adding model 'UserProfile'
        db.create_table(u'lizard_progress_userprofile', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], unique=True)),
            ('organization', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lizard_progress.Organization'])),
        ))
        db.send_create_signal(u'lizard_progress', ['UserProfile'])

        # Adding M2M table for field roles on 'UserProfile'
        db.create_table(u'lizard_progress_userprofile_roles', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('userprofile', models.ForeignKey(orm[u'lizard_progress.userprofile'], null=False)),
            ('userrole', models.ForeignKey(orm[u'lizard_progress.userrole'], null=False))
        ))
        db.create_unique(u'lizard_progress_userprofile_roles', ['userprofile_id', 'userrole_id'])

        # Adding model 'Project'
        db.create_table(u'lizard_progress_project', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('slug', self.gf('django.db.models.fields.SlugField')(unique=True, max_length=50)),
            ('organization', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lizard_progress.Organization'])),
            ('is_archived', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('project_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lizard_progress.ProjectType'], null=True, blank=True)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
        ))
        db.send_create_signal(u'lizard_progress', ['Project'])

        # Adding unique constraint on 'Project', fields ['name', 'organization']
        db.create_unique(u'lizard_progress_project', ['name', 'organization_id'])

        # Adding model 'Location'
        db.create_table(u'lizard_progress_location', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('activity', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lizard_progress.Activity'], null=True)),
            ('location_code', self.gf('django.db.models.fields.CharField')(max_length=50, db_index=True)),
            ('the_geom', self.gf('django.contrib.gis.db.models.fields.PointField')(srid=28992, null=True)),
            ('information', self.gf('jsonfield.fields.JSONField')(null=True, blank=True)),
            ('timestamp', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('complete', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal(u'lizard_progress', ['Location'])

        # Adding unique constraint on 'Location', fields ['location_code', 'activity']
        db.create_unique(u'lizard_progress_location', ['location_code', 'activity_id'])

        # Adding model 'AvailableMeasurementType'
        db.create_table(u'lizard_progress_availablemeasurementtype', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=50)),
            ('slug', self.gf('django.db.models.fields.SlugField')(unique=True, max_length=50)),
            ('implementation', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('default_icon_missing', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('default_icon_complete', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('can_be_displayed', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('needs_predefined_locations', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('likes_predefined_locations', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('needs_scheduled_measurements', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('description', self.gf('django.db.models.fields.TextField')(default=u'', blank=True)),
        ))
        db.send_create_signal(u'lizard_progress', ['AvailableMeasurementType'])

        # Adding model 'Activity'
        db.create_table(u'lizard_progress_activity', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lizard_progress.Project'])),
            ('name', self.gf('django.db.models.fields.CharField')(default=u'Activity name', max_length=100)),
            ('measurement_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lizard_progress.AvailableMeasurementType'], null=True)),
            ('contractor', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lizard_progress.Organization'], null=True)),
            ('source_activity', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lizard_progress.Activity'], null=True, blank=True)),
        ))
        db.send_create_signal(u'lizard_progress', ['Activity'])

        # Adding model 'MeasurementTypeAllowed'
        db.create_table(u'lizard_progress_measurementtypeallowed', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('organization', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lizard_progress.Organization'])),
            ('mtype', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lizard_progress.AvailableMeasurementType'])),
            ('visible', self.gf('django.db.models.fields.BooleanField')(default=True)),
        ))
        db.send_create_signal(u'lizard_progress', ['MeasurementTypeAllowed'])

        # Adding model 'Measurement'
        db.create_table(u'lizard_progress_measurement', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('location', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lizard_progress.Location'], null=True)),
            ('data', self.gf('jsonfield.fields.JSONField')(null=True)),
            ('date', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('the_geom', self.gf('django.contrib.gis.db.models.fields.PointField')(srid=28992, null=True, blank=True)),
            ('filename', self.gf('django.db.models.fields.CharField')(max_length=1000)),
            ('timestamp', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
        ))
        db.send_create_signal(u'lizard_progress', ['Measurement'])

        # Adding model 'Hydrovak'
        db.create_table(u'lizard_progress_hydrovak', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lizard_progress.Project'])),
            ('br_ident', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('the_geom', self.gf('django.contrib.gis.db.models.fields.MultiLineStringField')(srid=28992)),
        ))
        db.send_create_signal(u'lizard_progress', ['Hydrovak'])

        # Adding unique constraint on 'Hydrovak', fields ['project', 'br_ident']
        db.create_unique(u'lizard_progress_hydrovak', ['project_id', 'br_ident'])

        # Adding model 'UploadedFile'
        db.create_table(u'lizard_progress_uploadedfile', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('activity', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lizard_progress.Activity'], null=True)),
            ('uploaded_by', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('uploaded_at', self.gf('django.db.models.fields.DateTimeField')()),
            ('path', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('ready', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('success', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('linelike', self.gf('django.db.models.fields.BooleanField')(default=True)),
        ))
        db.send_create_signal(u'lizard_progress', ['UploadedFile'])

        # Adding model 'UploadedFileError'
        db.create_table(u'lizard_progress_uploadedfileerror', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('uploaded_file', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lizard_progress.UploadedFile'])),
            ('line', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('error_code', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('error_message', self.gf('django.db.models.fields.CharField')(max_length=300)),
        ))
        db.send_create_signal(u'lizard_progress', ['UploadedFileError'])

        # Adding model 'ExportRun'
        db.create_table(u'lizard_progress_exportrun', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('activity', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lizard_progress.Activity'], null=True)),
            ('exporttype', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('generates_file', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True, blank=True)),
            ('created_by', self.gf('django.db.models.fields.related.ForeignKey')(default=None, to=orm['auth.User'], null=True, blank=True)),
            ('file_path', self.gf('django.db.models.fields.CharField')(default=None, max_length=300, null=True)),
            ('ready_for_download', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('export_running', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('error_message', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
        ))
        db.send_create_signal(u'lizard_progress', ['ExportRun'])

        # Adding unique constraint on 'ExportRun', fields ['activity', 'exporttype']
        db.create_unique(u'lizard_progress_exportrun', ['activity_id', 'exporttype'])

        # Adding model 'UploadLog'
        db.create_table(u'lizard_progress_uploadlog', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lizard_progress.Project'])),
            ('uploading_organization', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lizard_progress.Organization'])),
            ('mtype', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lizard_progress.AvailableMeasurementType'])),
            ('when', self.gf('django.db.models.fields.DateTimeField')()),
            ('filename', self.gf('django.db.models.fields.CharField')(max_length=250)),
            ('num_measurements', self.gf('django.db.models.fields.IntegerField')()),
        ))
        db.send_create_signal(u'lizard_progress', ['UploadLog'])

        # Adding model 'OrganizationConfig'
        db.create_table(u'lizard_progress_organizationconfig', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('organization', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lizard_progress.Organization'])),
            ('config_option', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('value', self.gf('django.db.models.fields.CharField')(max_length=50, null=True, blank=True)),
        ))
        db.send_create_signal(u'lizard_progress', ['OrganizationConfig'])

        # Adding model 'ProjectConfig'
        db.create_table(u'lizard_progress_projectconfig', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lizard_progress.Project'])),
            ('config_option', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('value', self.gf('django.db.models.fields.CharField')(max_length=50, null=True)),
        ))
        db.send_create_signal(u'lizard_progress', ['ProjectConfig'])

        # Adding model 'ActivityConfig'
        db.create_table(u'lizard_progress_activityconfig', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('activity', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lizard_progress.Activity'])),
            ('config_option', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('value', self.gf('django.db.models.fields.CharField')(max_length=50, null=True)),
        ))
        db.send_create_signal(u'lizard_progress', ['ActivityConfig'])

        # Adding model 'LizardConfiguration'
        db.create_table(u'lizard_progress_lizardconfiguration', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('geoserver_database_engine', self.gf('django.db.models.fields.CharField')(max_length=300)),
            ('geoserver_table_name', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('upload_config', self.gf('django.db.models.fields.CharField')(max_length=300)),
            ('upload_url_template', self.gf('django.db.models.fields.CharField')(max_length=300)),
        ))
        db.send_create_signal(u'lizard_progress', ['LizardConfiguration'])


    def backwards(self, orm):
        # Removing unique constraint on 'ExportRun', fields ['activity', 'exporttype']
        db.delete_unique(u'lizard_progress_exportrun', ['activity_id', 'exporttype'])

        # Removing unique constraint on 'Hydrovak', fields ['project', 'br_ident']
        db.delete_unique(u'lizard_progress_hydrovak', ['project_id', 'br_ident'])

        # Removing unique constraint on 'Location', fields ['location_code', 'activity']
        db.delete_unique(u'lizard_progress_location', ['location_code', 'activity_id'])

        # Removing unique constraint on 'Project', fields ['name', 'organization']
        db.delete_unique(u'lizard_progress_project', ['name', 'organization_id'])

        # Removing unique constraint on 'ProjectType', fields ['name', 'organization']
        db.delete_unique(u'lizard_progress_projecttype', ['name', 'organization_id'])

        # Deleting model 'ErrorMessage'
        db.delete_table(u'lizard_progress_errormessage')

        # Deleting model 'Organization'
        db.delete_table(u'lizard_progress_organization')

        # Removing M2M table for field errors on 'Organization'
        db.delete_table('lizard_progress_organization_errors')

        # Deleting model 'ProjectType'
        db.delete_table(u'lizard_progress_projecttype')

        # Deleting model 'UserRole'
        db.delete_table(u'lizard_progress_userrole')

        # Deleting model 'UserProfile'
        db.delete_table(u'lizard_progress_userprofile')

        # Removing M2M table for field roles on 'UserProfile'
        db.delete_table('lizard_progress_userprofile_roles')

        # Deleting model 'Project'
        db.delete_table(u'lizard_progress_project')

        # Deleting model 'Location'
        db.delete_table(u'lizard_progress_location')

        # Deleting model 'AvailableMeasurementType'
        db.delete_table(u'lizard_progress_availablemeasurementtype')

        # Deleting model 'Activity'
        db.delete_table(u'lizard_progress_activity')

        # Deleting model 'MeasurementTypeAllowed'
        db.delete_table(u'lizard_progress_measurementtypeallowed')

        # Deleting model 'Measurement'
        db.delete_table(u'lizard_progress_measurement')

        # Deleting model 'Hydrovak'
        db.delete_table(u'lizard_progress_hydrovak')

        # Deleting model 'UploadedFile'
        db.delete_table(u'lizard_progress_uploadedfile')

        # Deleting model 'UploadedFileError'
        db.delete_table(u'lizard_progress_uploadedfileerror')

        # Deleting model 'ExportRun'
        db.delete_table(u'lizard_progress_exportrun')

        # Deleting model 'UploadLog'
        db.delete_table(u'lizard_progress_uploadlog')

        # Deleting model 'OrganizationConfig'
        db.delete_table(u'lizard_progress_organizationconfig')

        # Deleting model 'ProjectConfig'
        db.delete_table(u'lizard_progress_projectconfig')

        # Deleting model 'ActivityConfig'
        db.delete_table(u'lizard_progress_activityconfig')

        # Deleting model 'LizardConfiguration'
        db.delete_table(u'lizard_progress_lizardconfiguration')


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
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['lizard_progress.Project']"}),
            'source_activity': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['lizard_progress.Activity']", 'null': 'True', 'blank': 'True'})
        },
        u'lizard_progress.activityconfig': {
            'Meta': {'object_name': 'ActivityConfig'},
            'activity': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['lizard_progress.Activity']"}),
            'config_option': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True'})
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
            'Meta': {'unique_together': "((u'activity', u'exporttype'),)", 'object_name': 'ExportRun'},
            'activity': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['lizard_progress.Activity']", 'null': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'error_message': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'export_running': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'exporttype': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'file_path': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '300', 'null': 'True'}),
            'generates_file': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
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
            'Meta': {'ordering': "(u'location_code',)", 'unique_together': "((u'location_code', u'activity'),)", 'object_name': 'Location'},
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