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


admin.site.register(models.Hydrovak)
admin.site.register(models.Location)
admin.site.register(models.AvailableMeasurementType)
admin.site.register(models.Project)
admin.site.register(models.Activity)
admin.site.register(models.Organization, OrganizationAdmin)
admin.site.register(models.UserProfile)
admin.site.register(models.ErrorMessage)
admin.site.register(models.LizardConfiguration)
admin.site.register(models.ProjectType, ProjectTypeAdmin)
