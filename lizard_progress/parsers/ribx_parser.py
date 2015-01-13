from PIL.ImageFile import ImageFile
import logging

from ribxlib import parsers

from lizard_progress import models

from lizard_progress.specifics import ProgressParser
from lizard_progress.specifics import UnSuccessfulParserResult

logger = logging.getLogger(__name__)


class RibxParser(ProgressParser):
    ERRORS = {
        'LOCATION_NOT_FOUND': "Onbekende buis '{}'.",
        }

    def parse(self, check_only=False):
        if isinstance(self.file_object, ImageFile):
            return UnSuccessfulParserResult()

        ribx_parser = parsers.RibxParser()
        ribx_parser.parse(self.file_object)

        for pipe in ribx_parser.pipes():
            try:
                location = self.activity.location_set.objects.get(
                    location_code=pipe.ref)
            except models.Location.DoesNotExist:
                self.record_error(
                    10, 'LOCATION_NOT_FOUND',
                    unicode(
                        self.ERRORS['LOCATION_NOT_FOUND'].format(pipe.ref)))

            # Always make a new measurement! Never update existing ones.
            measurement = models.Measurement.objects.create(
                location=location)
