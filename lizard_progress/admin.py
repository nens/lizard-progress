from django.contrib import admin
from lizard_progress.models import Project
from lizard_progress.models import Contractor
from lizard_progress.models import Area
from lizard_progress.models import Location
from lizard_progress.models import MeasurementType

admin.site.register(Project)
admin.site.register(Contractor)
admin.site.register(Area)
admin.site.register(Location)
admin.site.register(MeasurementType)
