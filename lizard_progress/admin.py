"""Settings for the Admin pages"""

from django.contrib import admin

from lizard_progress import models


class OrganizationConfigurationInline(admin.TabularInline):
    model = models.OrganizationConfig


class OrganizationAdmin(admin.ModelAdmin):
    filter_horizontal = ['errors']
    inlines = [OrganizationConfigurationInline]


admin.site.register(models.Area)
admin.site.register(models.Contractor)
admin.site.register(models.Hydrovak)
admin.site.register(models.Location)
admin.site.register(models.AvailableMeasurementType)
admin.site.register(models.MeasurementType)
admin.site.register(models.Project)
admin.site.register(models.Organization, OrganizationAdmin)
admin.site.register(models.UserProfile)
admin.site.register(models.ErrorMessage)
admin.site.register(models.LizardConfiguration)
