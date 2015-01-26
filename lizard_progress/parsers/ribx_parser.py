# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

# Python 3 is coming
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import itertools

from PIL.ImageFile import ImageFile
import logging

from ribxlib import parsers

from lizard_progress import models

from lizard_progress.specifics import ProgressParser
from lizard_progress.specifics import UnSuccessfulParserResult

logger = logging.getLogger(__name__)


class RibxParser(ProgressParser):
    ERRORS = {
        'LOCATION_NOT_FOUND': "Onbekende streng/put/kolk ref '{}'.",
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

        for item in itertools.chain(ribx.pipes, ribx.manholes, ribx.drains):
            measurement = self.save_measurement(item)
            if measurement is not None:
                measurements.append(measurement)

        if not measurements:
            self.record_error(0, None, 'Bestand bevat geen gegevens.')

        return self._parser_result(measurements)

    def save_measurement(self, item):
        """item is a pipe, drain or manhole object that has properties
        'ref', 'inspection_date', 'geom' and optionally 'media'."""
        try:
            location = self.activity.location_set.get(
                location_code=item.ref)
        except models.Location.DoesNotExist:
            self.record_error(
                item.sourceline, 'LOCATION_NOT_FOUND',
                self.ERRORS['LOCATION_NOT_FOUND'].format(item.ref))
            return None

        # If measurement already exists with the same date, this upload
        # isn't new and we don't have to save it. If it doesn't exist
        # with this date, add a new measurement, don't overwrite the
        # old one.
        measurement, created = models.Measurement.objects.get_or_create(
            location=location, date=item.inspection_date)
        if created:
            measurement.data = {'filetype': 'ribx'}  # As opposed to media
            measurement.record_location(item.geom)  # Saves

        # Check which files are expected to be uploaded along with this
        # measurement.
        complete = True
        for filename in getattr(item, 'media', ()):
            expected_attachment, created = (
                models.ExpectedAttachment.objects.get_or_create(
                    activity=self.activity,
                    filename=filename))
            location.expected_attachments.add(expected_attachment)
            if not expected_attachment.uploaded:
                complete = False

        location.complete = complete
        location.save()

        return measurement
