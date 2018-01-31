"""Settings for the Admin pages"""

from django.contrib import admin

from lizard_progress import models


class OrganizationConfigurationInline(admin.TabularInline):
    model = models.OrganizationConfig


class MtypeAllowedInline(admin.TabularInline):
    model = models.Organization.mtypes_allowed.through


class OrganizationAdmin(admin.ModelAdmin):
    filter_horizontal = ['errors']
    inlines = [OrganizationConfigurationInline, MtypeAllowedInline]


class ProjectTypeAdmin(admin.ModelAdmin):

    list_display = ('id', 'name', 'organization', 'default')
    list_editable = ('name', 'organization', 'default')


class ExportRunAdmin(admin.ModelAdmin):
    search_fields = ['activity__name', 'exporttype']


class MeasurementAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'base_filename', 'num_expected_attachments', 'timestamp')
    search_fields = [
        'location__location_code', 'rel_file_path',
        'location__activity__project__name']
    ordering = ('-timestamp',)

    def num_expected_attachments(self, obj):
        return obj.expected_attachments.count()


class LocationAdmin(admin.ModelAdmin):
    list_display = ('location_code', 'location_type', 'activity', 'timestamp')
    search_fields = [
        'location_code', 'location_type', 'activity__name',
        'activity__project__name']
    ordering = ('-timestamp',)


class UploadedFileAdmin(admin.ModelAdmin):
    list_display = ('rel_file_path', 'uploaded_by', 'uploaded_at')
    list_filter = ('ready', 'success', 'linelike')
    search_fields = ['activity__name', 'rel_file_path']
    ordering = ('-uploaded_at',)


class UploadedFileErrorAdmin(admin.ModelAdmin):
    raw_id_fields = ['uploaded_file']


class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'organization', 'is_archived')
    search_fields = ['name', 'slug', 'organization__name']
    list_filter = ['organization__name']


class ActivityAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'measurement_type', 'contractor')
    search_fields = [
        'project__name', 'name', 'measurement_type__name', 'contractor__name']
    list_select_related = ['contractor', 'project', 'measurement_type']


class ExpectedAttachmentAdmin(admin.ModelAdmin):
    search_fields = ['filename']
    list_display = ('filename', 'uploaded')


class AcceptedFileAdmin(admin.ModelAdmin):
    list_display = ('activity', 'rel_file_path', 'file_size',
                    'last_downloaded_at', 'uploaded_at')
    search_fields = ['activity', 'rel_file_path']


class ReviewProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'organization', 'project', 'ribx_file',
                    'inspection_filler' )
    search_fields = ['name', 'organization', 'project']


admin.site.register(models.Hydrovak)
admin.site.register(models.Location, LocationAdmin)
admin.site.register(models.AvailableMeasurementType)
admin.site.register(models.Project, ProjectAdmin)
admin.site.register(models.Activity, ActivityAdmin)
admin.site.register(models.Organization, OrganizationAdmin)
admin.site.register(models.UserProfile)
admin.site.register(models.UserRole)
admin.site.register(models.ErrorMessage)
admin.site.register(models.LizardConfiguration)
admin.site.register(models.ProjectType, ProjectTypeAdmin)
admin.site.register(models.ExportRun, ExportRunAdmin)
admin.site.register(models.ExpectedAttachment, ExpectedAttachmentAdmin)
admin.site.register(models.MeasurementTypeAllowed)
admin.site.register(models.Measurement, MeasurementAdmin)
admin.site.register(models.UploadedFile, UploadedFileAdmin)
admin.site.register(models.UploadedFileError, UploadedFileErrorAdmin)
admin.site.register(models.UploadLog)
admin.site.register(models.AcceptedFile, AcceptedFileAdmin)
admin.site.register(models.ReviewProject, ReviewProjectAdmin)
