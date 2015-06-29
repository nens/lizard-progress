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
        'X_NOT_IN_EXTENT': "Buiten gebied: X coördinaat niet tussen {} en {}.",
        'Y_NOT_IN_EXTENT': "Buiten gebied: Y coördinaat niet tussen {} en {}.",
        'ATTACHMENT_ALREADY_EXISTS':
        "Er is al eerder een bestand met de naam '{}' geupload. "
        "Kies een nieuwe naam.",
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

        # Use these to check whether locations are inside extent
        min_x = self.activity.config_value('minimum_x_coordinate')
        max_x = self.activity.config_value('maximum_x_coordinate')
        min_y = self.activity.config_value('minimum_y_coordinate')
        max_y = self.activity.config_value('maximum_y_coordinate')

        for item in itertools.chain(ribx.pipes, ribx.manholes, ribx.drains):
            error = False
            if item.geom:
                if not (min_x <= item.geom.GetX() <= max_x):
                    self.record_error(
                        item.sourceline, 'X_NOT_IN_EXTENT',
                        self.ERRORS['X_NOT_IN_EXTENT'].format(min_x, max_x))
                    error = True
                if not (min_y <= item.geom.GetY() <= max_y):
                    self.record_error(
                        item.sourceline, 'Y_NOT_IN_EXTENT',
                        self.ERRORS['Y_NOT_IN_EXTENT'].format(min_y, max_y))
                    error = True

            if not error:
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

        # If measurement already exists with the same date, this
        # upload isn't new and we don't have to add a new Measurement
        # instance for it. Details (like the associated files) may still have
        # changed.
        # If it doesn't exist with this date, add a
        # new measurement, don't overwrite the old one.
        measurement = self.find_existing_ribx_measurement(
            location, item.inspection_date)

        if measurement is None:
            measurement = models.Measurement(
                location=location,
                date=item.inspection_date,
                data={'filetype': 'ribx'})

        # Record the location regardless of whether it was uploaded before --
        # maybe someone corrected the previous upload.
        measurement.record_location(item.geom)  # Saves
        associated_files = getattr(item, 'media', ())

        try:
            measurement.setup_expected_attachments(associated_files)
        except models.AlreadyUploadedError as e:
            self.record_error(
                item.sourceline, 'ATTACHMENT_ALREADY_EXISTS',
                self.ERRORS['ATTACHMENT_ALREADY_EXISTS'].format(e.filename))
            return None

        # Update completeness of location
        location.set_completeness()

        return measurement

    def find_existing_ribx_measurement(self, location, inspection_date):
        for measurement in models.Measurement.objects.filter(
                location=location, date=inspection_date):
            if (measurement.data and
                    measurement.data.get('filetype') == 'ribx'):
                return measurement

        return None
