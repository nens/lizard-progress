# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

# Python 3 is coming
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

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

        ribx, errors = parsers.parse(
            self.file_object, parsers.Mode.INSPECTION)

        if errors:
            for error in errors:
                self.record_error(error['line'], None, error['message'])
            return self._parser_result([])

        measurements = []

        for pipe in ribx.pipes:
            try:
                location = self.activity.location_set.get(
                    location_code=pipe.ref)
            except models.Location.DoesNotExist:
                self.record_error(
                    None, 'LOCATION_NOT_FOUND',
                    self.ERRORS['LOCATION_NOT_FOUND'].format(pipe.ref))

            # Always make a new measurement! Never update existing ones.
            measurement = models.Measurement.objects.create(
                location=location)
            measurement.date = pipe.inspection_date
            measurement.data = {'filetype': 'ribx'}  # As opposed to media
            measurement.record_location(pipe.geom)  # Saves

            location.complete = True
            location.save()

            measurements.append(measurement)

        return self._parser_result(measurements)
