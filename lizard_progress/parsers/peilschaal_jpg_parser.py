from PIL.ImageFile import ImageFile
from math import sqrt
import logging
import os.path

from django.contrib.gis.geos import Point

from lizard_map.coordinates import wgs84_to_rd
from lizard_progress.models import Location
from lizard_progress.models import Measurement
from lizard_progress.models import SRID
from lizard_progress.specifics import ProgressParser
from lizard_progress.specifics import FILE_IMAGE
from lizard_progress.specifics import SuccessfulParserResult
from lizard_progress.specifics import UnSuccessfulParserResult
from lizard_progress.util.image import get_exif_data, get_lat_lon

logger = logging.getLogger(__name__)


class PeilschaalJpgParser(ProgressParser):
    """Parser for the JPG photos uploaded for the Peilschalen project."""

    ERRORS = {
        'location': "Peilschaal ID onbekend: %s",
        'gps': "Foto mist GPS-data.",
        'toofar': ("De afstand tussen de locatie en de "
                   "foto-data is te groot (%.1fm)."),
        'scheduled': "Meting met id %s en type %s was niet gepland.",
        }

    FILE_TYPE = FILE_IMAGE

    def parse(self, check_only=False):
        logger.critical("In parser")
        if not isinstance(self.file_object, ImageFile):
            logger.critical("No ImageFile")
            return UnSuccessfulParserResult()

        # Uniek_id: Part of the filename before the extension, in
        # upper case.
        uniek_id = os.path.splitext(self.file_object.name)[0].upper()

        try:
            location = Location.objects.get(
                location_code=uniek_id,
                activity=self.activity)
        except Location.DoesNotExist:
            return self.error(uniek_id)

        exif_data = get_exif_data(self.file_object)
        lat, lon = get_lat_lon(exif_data)

        if not lat or not lon:
            return self.error('gps')

        x, y = wgs84_to_rd(lon, lat)
        x0, y0 = location.the_geom.x, location.the_geom.y
        d = sqrt((x - x0) ** 2 + (y - y0) ** 2)

        if d > 75.0:
            return self.error('toofar', d)

        if not check_only:
            m, _ = Measurement.objects.get_or_create(
                location=location)

            m.data = {}
            m.date = None
            m.the_geom = Point(x, y, srid=SRID)
            m.save()

            location.complete = True
            location.save()
            measurements = (m,)
        else:
            measurements = ()

        return SuccessfulParserResult(measurements)
