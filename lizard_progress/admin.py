"""Settings for the Admin pages"""

from django.contrib import admin
from lizard_progress.models import Area
from lizard_progress.models import Contractor
from lizard_progress.models import Hydrovak
from lizard_progress.models import Location
from lizard_progress.models import MeasurementType
from lizard_progress.models import AvailableMeasurementType
from lizard_progress.models import Project
from lizard_progress.models import Organization
from lizard_progress.models import UserProfile

admin.site.register(Area)
admin.site.register(Contractor)
admin.site.register(Hydrovak)
admin.site.register(Location)
admin.site.register(AvailableMeasurementType)
admin.site.register(MeasurementType)
admin.site.register(Project)
admin.site.register(Organization)
admin.site.register(UserProfile)
