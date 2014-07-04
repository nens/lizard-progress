"""Parsers for files uploaded to the upload server. The parsers()
functions in hdsr.progress.py return the function in this file to
lizard-progress, which then calls them."""

from PIL.ImageFile import ImageFile
from math import sqrt
import logging
import os.path

from django.contrib.gis.geos import Point

from lizard_map.coordinates import wgs84_to_rd
from lizard_progress.models import Location
from lizard_progress.models import Measurement
from lizard_progress.models import MeasurementType
from lizard_progress.models import SRID
from lizard_progress.models import ScheduledMeasurement
from lizard_progress.specifics import ProgressParser
from lizard_progress.specifics import UnSuccessfulParserResult
from lizard_progress.util.image import get_exif_data, get_lat_lon

logger = logging.getLogger(__name__)


class OeverfotoParser(ProgressParser):
    """Process JPG images for the dwarsprofielen project. The images
    must have filenames of a given format and have GPS data that is
    close to the scheduled location."""

    ERRORS = {
        'notleftright': "Foto is geen linker (_L) of rechter (_R) oever.",
        'nolocation': "ProfielIdentificatie onbekend: %s",
        'nogps': "Foto mist GPS-data.",
        'toofar': ("De afstand tussen de locatie en "
                   "de foto-data is te groot (%.1fm)."),
        'notscheduled': "Meting met id %s en type %s was niet gepland.",
        }

    def parse(self, check_only=False):
        if not isinstance(self.file_object, ImageFile):
            return UnSuccessfulParserResult()

        # Filename is of the format "ID_L" or "ID_R", possibly in
        # mixed case. Since IDs are upper case, we change the filename
        # to upper case first.
        filename_no_suffix = os.path.splitext(self.file_object.name)[0].upper()

        is_left = filename_no_suffix.endswith('_L')
        is_right = filename_no_suffix.endswith('_R')
        if not (is_left or is_right):
            return self.error('notleftright')

        uniek_id = filename_no_suffix[:-2]

        try:
            location = Location.objects.get(
                location_code=uniek_id,
                project=self.project)
        except Location.DoesNotExist:
            return self.error('nolocation', uniek_id)

        exif_data = get_exif_data(self.file_object)
        lat, lon = get_lat_lon(exif_data)

        if not lat or not lon:
            return self.error('gps')

        x, y = wgs84_to_rd(lon, lat)
        x0, y0 = location.the_geom.x, location.the_geom.y
        d = sqrt((x - x0) ** 2 + (y - y0) ** 2)

        if d > 75.0:
            return self.error('toofar', d)

        measurement_type = self.mtype()
        try:
            scheduled_measurement = (ScheduledMeasurement.objects.
                                     get(project=self.project,
                                         contractor=self.contractor,
                                         location=location,
                                         measurement_type=measurement_type))
        except ScheduledMeasurement.DoesNotExist:
            return self.error('notscheduled', id, str(measurement_type))

        # Several measurements per scheduled measurement, find if ours exists
        # The measurements store 'left' or 'right' in the data field.
        data_field = 'left' if is_left else 'right'

        if not check_only:
            measurements = {}
            for m in scheduled_measurement.measurement_set.all():
                measurements[m.data] = m

            if data_field in measurements:
                measurement = measurements[data_field]
            else:
                # New
                measurement = Measurement(
                    scheduled=scheduled_measurement, data=data_field)
            measurements[data_field] = measurement

            measurement.date = None
            measurement.the_geom = Point(x, y, srid=SRID)
            measurement.save()

            if 'left' in measurements and 'right' in measurements:
                scheduled_measurement.complete = True
                scheduled_measurement.save()

            return self.success((measurement,))
        else:
            return self.success(())
