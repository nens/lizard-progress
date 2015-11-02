# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

# Python 3 is coming
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import itertools
import json

from PIL.ImageFile import ImageFile
import logging
import os

from django.conf import settings
from django.contrib.sites.models import Site
from django.utils import translation

from ribxlib import models as ribxmodels
from ribxlib import parsers

from lizard_progress import models
from lizard_progress.changerequests.models import Request
from lizard_progress.email_notifications.models import NotificationType
from lizard_progress.util import geo
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

        measurements = self.get_measurements(ribx)

        if not measurements:
            self.record_error(0, None, 'Bestand bevat geen gegevens.')

        return self._parser_result(measurements)

    def get_measurements(self, ribx):
        # Use these to check whether locations are inside extent
        self.min_x = self.activity.config_value('minimum_x_coordinate')
        self.max_x = self.activity.config_value('maximum_x_coordinate')
        self.min_y = self.activity.config_value('minimum_y_coordinate')
        self.max_y = self.activity.config_value('maximum_y_coordinate')

        measurements = []
        for item in itertools.chain(
                ribx.inspection_pipes, ribx.cleaning_pipes,
                ribx.inspection_manholes, ribx.cleaning_manholes,
                ribx.drains):
            error = self.check_coordinates(item)
            if not error:
                if item.work_impossible:
                    # This is not a measurement, but a claim that the
                    # assigned work couldn't be done. Open a deletion
                    # request instead of recording a measurement.
                    # Creating the request also automatically
                    # sends an email notification.
                    self.create_deletion_request(item)
                else:
                    measurement = self.save_measurement(item)
                    if measurement is not None:
                        measurements.append(measurement)

        return measurements

    def check_coordinates(self, item):
        error = False
        if item.geom:
            if not (self.min_x <= item.geom.GetX() <= self.max_x):
                self.record_error(
                    item.sourceline, 'X_NOT_IN_EXTENT',
                    self.ERRORS['X_NOT_IN_EXTENT'].format(
                        self.min_x, self.max_x))
                error = True
            if not (self.min_y <= item.geom.GetY() <= self.max_y):
                self.record_error(
                    item.sourceline, 'Y_NOT_IN_EXTENT',
                    self.ERRORS['Y_NOT_IN_EXTENT'].format(
                        self.min_y, self.max_y))
                error = True
        return error

    def create_deletion_request(self, item):
        # Deletion requests can only handle point geometries;
        # if geom is a line, take its midpoint.
        geom = item.geom
        if geo.is_line(geom):
            geom = geo.get_midpoint(geom)

        try:
            location = self.activity.location_set.get(location_code=item.ref)
            Request.create_deletion_request(
                location, motivation=item.work_impossible,
                user_is_manager=False, geom=geom)
        except models.Location.DoesNotExist:
            # Already deleted?
            pass

    def save_measurement(self, item):
        """item is a pipe, drain or manhole object that has properties
        'ref', 'inspection_date', 'geom' and optionally 'media'."""
        try:
            location = self.activity.location_set.get(
                location_code=item.ref)
        except models.Location.DoesNotExist:
            if not item.new:
                self.record_error(
                    item.sourceline, 'LOCATION_NOT_FOUND',
                    self.ERRORS['LOCATION_NOT_FOUND'].format(item.ref))
                return None
            else:
                location = self.create_new(item)

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
            all_uploaded = measurement.setup_expected_attachments(
                associated_files)
        except models.AlreadyUploadedError as e:
            self.record_error(
                item.sourceline, 'ATTACHMENT_ALREADY_EXISTS',
                self.ERRORS['ATTACHMENT_ALREADY_EXISTS'].format(e.filename))
            return None

        # Update completeness of location
        location.complete = all_uploaded
        location.save()

        return measurement

    def find_existing_ribx_measurement(self, location, inspection_date):
        for measurement in models.Measurement.objects.filter(
                location=location, date=inspection_date):
            if (measurement.data and
                    measurement.data.get('filetype') == 'ribx'):
                return measurement

        return None

    def create_new(self, item):
        """This item is marked as new. Create it and send mail."""

        is_point = True
        if isinstance(item, ribxmodels.Pipe):
            location_type = models.Location.LOCATION_TYPE_PIPE
            is_point = False
        elif isinstance(item, ribxmodels.Manhole):
            location_type = models.Location.LOCATION_TYPE_MANHOLE
        elif isinstance(item, ribxmodels.Drain):
            location_type = models.Location.LOCATION_TYPE_DRAIN
        else:
            # Huh?
            location_type = models.Location.LOCATION_TYPE_POINT

        location = models.Location.objects.create(
            activity=self.activity,
            location_code=item.ref,
            location_type=location_type,
            the_geom=item.geom.ExportToWkt(),
            is_point=is_point,
            information=json.dumps({
                "remark": "Added automatically by {}".format(
                    self.file_object.name)}))

        notification_type = NotificationType.objects.get(
            name='new location from ribx')
        location_link = (
            Site.objects.get_current().domain +
            location.get_absolute_url())

        with translation.override(settings.LANGUAGE_CODE):
            # Let terms like 'pipe' be translated to Dutch
            target = unicode(location)

        self.activity.notify_managers(
            notification_type,
            actor=unicode(self.activity.contractor),
            action_object=os.path.basename(self.file_object.name),
            target=target,
            extra={'link': location_link})

        return location
