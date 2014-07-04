from PIL.ImageFile import ImageFile
import csv
import logging

from lizard_progress.models import Location
from lizard_progress.models import Measurement
from lizard_progress.models import MeasurementType
from lizard_progress.models import ScheduledMeasurement
from lizard_progress.specifics import ProgressParser
from lizard_progress.specifics import UnSuccessfulParserResult

logger = logging.getLogger(__name__)


class OeverkenmerkParser(ProgressParser):
    """Parse CSV files for the 'oeverkenmerk' measurement type of the
    Dwarsprofielen project."""

    ERRORS = {
        'elements': "Regel met %d elementen gevonden.",
        'location': ("Locatie %s niet gevonden."),
        'scheduled': "Meting %s %s %s %s was niet gepland.",
        'description': 'Missende of onbekende omschrijving bij ID %s.',
        }

    def parse(self, check_only=False):
        if isinstance(self.file_object, ImageFile):
            return UnSuccessfulParserResult()

        csvfile = csv.reader(self.file_object)

        # Skip first line
        csvfile.next()

        def desc(code):
            """Turn code into description, or None if unknown."""
            return {
                'TI': 'Traditioneel ingericht',
                'NV': 'Natuurvriendelijk ingericht',
                'NI': 'Niet ingericht',
            }.get(code, None)

        result_measurements = []

        for row in csvfile:
            if len(row) == 0:
                break

            if len(row) != 3:
                return self.error('elements', len(row))

            profielid, left, right = row

            # Fix wrong id
            l = None
            try:
                l = Location.objects.get(
                    location_code=profielid,
                    project=self.project)
            except Location.DoesNotExist:
                try:
                    parts = profielid.split('-')
                    if len(parts) == 3:
                        fixed_id = "%s-%s_%s" % tuple(parts)
                        l = Location.objects.get(
                            location_code=fixed_id,
                            project=self.project)
                except Location.DoesNotExist:
                    pass

            if l is None:
                return self.error('location', profielid)

            mtype = self.mtype()
            try:
                sm = ScheduledMeasurement.objects.get(
                    project=self.project, contractor=self.contractor,
                    measurement_type=mtype, location=l)
            except ScheduledMeasurement.DoesNotExist:
                return self.error('scheduled', self.project.name,
                                  self.contractor.name,
                                  mtype.name, l.location_code)

            descleft = desc(left)
            descright = desc(right)
            if descleft is None or descright is None:
                return self.error('description', l.location_code)

            if not check_only:
                m, _ = Measurement.objects.get_or_create(scheduled=sm)
                m.data = {
                    'left': left,
                    'description_left': desc(left),
                    'right': right,
                    'description_right': desc(right),
                    }
                m.save()
                result_measurements.append(m)

                sm.complete = True
                sm.save()

        return self.success(result_measurements)
