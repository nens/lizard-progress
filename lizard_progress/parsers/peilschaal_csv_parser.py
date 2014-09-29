from PIL.ImageFile import ImageFile
import csv
import logging

from lizard_progress.models import Location
from lizard_progress.models import Measurement
from lizard_progress.specifics import ProgressParser
from lizard_progress.specifics import UnSuccessfulParserResult

logger = logging.getLogger(__name__)


class PeilschaalCsvParser(ProgressParser):
    """Parser for the CSV files collected by the Peilschalen project."""
    ERRORS = {
        'elements': "Regel met %d elementen gevonden.",
        'missingdata': "Missende data op regel %s",
        'location': "Locatie %s niet gevonden.",
        'scheduled': "Meting %s %s %s %s was niet gepland.",
        }

    def parse(self, check_only=False):
        if isinstance(self.file_object, ImageFile):
            return UnSuccessfulParserResult()

        csvfile = csv.reader(self.file_object)

        # Skip first line
        csvfile.next()

        measurements = []

        for row in csvfile:
            if len(row) == 0:
                break

            if len(row) != 6:
                return self.error('elements', len(row))

            locationid, date, time, peilschaal, measurement, comment = row

            # Check: either id, date, time, peilschaal, measurement are
            # all filled in (and possibly comment), or none are filled in
            # and comment is.
            filled_in = (bool(x) for x in (
                locationid, date, time, peilschaal, measurement))
            not_filled_in = (not x for x in filled_in)

            if all(filled_in):
                pass
            elif all(not_filled_in) and comment:
                pass
            else:
                return self.error('missingdata', str(row))

            try:
                location = Location.objects.get(
                    location_code=locationid,
                    activity=self.activity)
            except Location.DoesNotExist:
                if self.activity.needs_predefined_locations():
                    return self.error('location', locationid)
                else:
                    location, created = Location.objects.get_or_create(
                        location_code=locationid,
                        activity=self.activity)

            if not check_only:
                m, _ = Measurement.objects.get_or_create(location=location)
                m.data = {
                    'date': date,
                    'time': time,
                    'peilschaal': peilschaal,
                    'measurement': measurement,
                    'comment': comment,
                    }
                m.save()
                location.complete = True
                location.save()
                measurements.append(m)

        return self.success(measurements)
