from django.contrib import admin
from lizard_progress.models import Project, Contractor, Area, Location, MeasurementType, ScheduledMeasurement, Measurement

admin.site.register(Project)
admin.site.register(Contractor)
admin.site.register(Area)
admin.site.register(Location)
admin.site.register(MeasurementType)
