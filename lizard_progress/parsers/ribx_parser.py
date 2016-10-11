# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

# Python 3 is coming
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from contextlib import contextmanager
import itertools
import json
import logging
import os
import time

from PIL.ImageFile import ImageFile
import requests
from osgeo import ogr

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


def _get_log_content(record_id):
    """Do a request to the GWSW API and get the response.

    Raises:
        ValueError: if the get response isn't proper JSON
        KeyError: if the JSON doesn't contain the 'logcontent' key
    """
    r_getlog = requests.get(settings.GWSW_GETLOG_URL % record_id)
    j = json.loads(r_getlog.text)
    log_content = j['logcontent']
    return log_content


def get_log_content(filename, retries=10, initial_wait=2):
    """Get the log from an uploaded ribx file.

    Args:
        filename: name of the file
        retries: max number of retries to the HTTP API
        initial_wait: a guess on how the external API takes to process the
            ribx file
    """
    tries = 1 + retries  # We try and retry, just like in life.
    time.sleep(initial_wait)
    for i in range(tries):
        logger.debug("get_log_content try number %s", i)
        log_content = _get_log_content(filename)
        # If the ribx file has not yet been processed you will get a
        # log_content with the value ['']. This join operation is to guard
        # against these blank values.
        if ''.join(log_content) == '':
            time.sleep(2*i**2 + 1)
        else:
            logger.debug("get_log_content succesful")
            return log_content
    return None


def parse_log_content(log_content):
    """Parse a log content, which is a list of strings.

    Example line:
    'Regel[93] - Fout*: verplicht <ABP> element voor deze <ZB_A> ontbreekt.'
    """
    errors = []
    for line in log_content:
        if line.lower().startswith('regel'):
            try:
                l, msg = line.split('-', 1)
            except ValueError:
                logger.exception("Can't split correctly: %s", line)
                continue
            try:
                line_no = int(l.strip()[6:-1])
            except ValueError:
                logger.exception("Can't convert line number: %s", l)
                continue
            error = {
                'line': line_no,
                'message': 'GWSW' + msg
                }
            errors.append(error)
    return errors


@contextmanager
def reopen_file(file_obj, mode):
    """Reopen a file object."""
    filepath = os.path.abspath(file_obj.name)
    try:
        f = open(filepath, mode)
        yield f
    finally:
        f.close()


def check_gwsw(file_obj):
    """Check the ribx file using the RIONED GWSW HTTP API.

    What is a little weird is that we re-open the file object. For some reason
    the opened file object is not usable; after re-opening it as 'rb' it
    works though. The cause is probably that the file has already been read,
    so the cursor is at the end of the file. file_obj.seek(0) is a possible
    alternative fix, but less clear...

    Raises:
        ValueError, KeyError, requests.exceptins.HTTPError
    """
    with reopen_file(file_obj, 'rb') as f:
        logger.info("Uploading file to RIONED GWSW API...")
        r_upload = requests.post(settings.GWSW_UPLOAD_URL,
                                 files={file_obj.name: f})
    logger.info("GWSW Upload response: %s", r_upload.text)
    errors = []
    if r_upload.ok:
        record_id = None
        try:
            resp = json.loads(r_upload.text)
            record_id = int(resp['id'])
        except (ValueError, KeyError):
            logger.exception("Can't get id from response: %s", r_upload)
            raise
        try:
            log_content = get_log_content(record_id, retries=10)
            errors = parse_log_content(log_content)
        except (ValueError, KeyError):
            logger.exception("Incorrect getlog response for id: %s",
                             record_id)
            raise
        return errors
    else:
        logger.error("Can't make request to %s", r_upload.url)
        r_upload.raise_for_status()


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

        ribx, ribx_errors = parsers.parse(
            self.file_object, parsers.Mode.INSPECTION)

        if ribx_errors:
            for error in ribx_errors:
                self.record_error(error['line'], None, error['message'])
            # Return, because unusable XML.
            return self._parser_result([])

        if settings.GWSW_API_ENABLED:
            try:
                gwsw_errors = check_gwsw(self.file_object)
            except (ValueError, KeyError, requests.exceptions.HTTPError):
                logger.exception("There is an error with (handling) the API")
            else:
                for error in gwsw_errors:
                    self.record_error(error['line'], None, error['message'])

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
                    # This is not a measurement, but a claim that (1) the
                    # assigned work couldn't be done OR (2) that the location
                    # of the object wasn't found (don't ask). Open a deletion
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
        'ref', 'inspection_date', 'geom' and optionally 'media'.

        Note: the behavior of this method changes depending on the attributes
        of the item (i.e.: 'work_impossible', 'new')
        """
        try:
            location = self.activity.location_set.get(
                location_code=item.ref)
        except models.Location.DoesNotExist:
            # The reason for this check is because of the altered
            # get_measurements in the RibxReinigingKolkenParser. Via the
            # RibxParser you can't get here. It probably doesn't do much
            # though.
            if item.work_impossible:
                return None
            elif not item.new:
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

        if is_point:
            # Biggest BS ever: The item.geom is a Point which contains x, y,
            # and z values. However, the GeometryField in the Location model
            # doesn't accept z-values (maybe only for points?). So we need to
            # do this elaborate conversion just to get a Point with ONLY x and
            # y values! Perhaps a better way to do this is is to correctly
            # parse the Points as 2D in the ribxlib...
            point_2d = ogr.Geometry(ogr.wkbPoint)
            point_2d.AddPoint_2D(item.geom.GetX(), item.geom.GetY())
            geom = point_2d
        else:
            geom = item.geom

        location = models.Location.objects.create(
            activity=self.activity,
            location_code=item.ref,
            location_type=location_type,
            the_geom=geom.ExportToWkt(),
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


class RibxReinigingInspectieRioolParser(RibxParser):
    """Parser with specifics for pipe inspections."""

    def find_existing_ribx_measurement(self, location, inspection_date,
                                       manhole_start):
        for measurement in models.Measurement.objects.filter(
                location=location, date=inspection_date):
            if (measurement.data and
                    measurement.data.get('filetype') == 'ribx' and
                    measurement.data.get('manhole_start') == manhole_start):
                return measurement
        return None

    def find_existing_ribx_measurements(self, location, inspection_date):
        """Find the measurements that were inspected on the same date and in
        the same location.

        Returns:
            a list of Measurements."""
        measurements = []
        for measurement in models.Measurement.objects.filter(
                location=location, date=inspection_date):
            if (measurement.data and
                    measurement.data.get('filetype') == 'ribx'):
                measurements.append(measurement)
        return measurements

    def save_measurement(self, item):
        """item is a pipe, drain or manhole object that has properties
        'ref', 'inspection_date', 'geom' and optionally 'media'.

        Note: the behavior of this method changes depending on the attributes
        of the item (i.e.: 'work_impossible', 'new')
        """
        try:
            location = self.activity.location_set.get(
                location_code=item.ref)
        except models.Location.DoesNotExist:
            # The reason for this check is because of the altered
            # get_measurements in the RibxReinigingKolkenParser. Via the
            # RibxParser you can't get here. It probably doesn't do much
            # though.
            if item.work_impossible:
                return None
            elif not item.new:
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
            location, item.inspection_date, item.manhole_start)

        if measurement is None:
            measurement = models.Measurement(
                location=location,
                date=item.inspection_date,
                data={'filetype': 'ribx', 'manhole_start': item.manhole_start})

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
                self.ERRORS['ATTACHMENT_ALREADY_EXISTS'].format(
                    e.filename))
            return None



        # Multiple measurements can belong to one location for pipe
        # inspections. To determine the completeness of one location, we now
        # have to determine the completeness of all related measurements
        # and 'and' them together.
        related_measurements = self.find_existing_ribx_measurements(
            location, item.inspection_date)
        # related_measurements = location.measurement_set.filter(parent=None)
        # import pdb; pdb.set_trace()
        for ms in related_measurements:
            all_uploaded = all_uploaded and bool(ms.missing_attachments())




        # Update completeness of location
        location.complete = all_uploaded
        location.save()

        return measurement


class RibxReinigingKolkenParser(RibxParser):
    """Special parser for drains.

    The reason for this parser is that we do not want to create Requests
    for work_impossible entries. Normally we do want that, but for drains
    we do not. Additionally, if applicable, we set the
    Location.work_impossible, and Location.new flags so that they can be
    visualized.
    """
    # TODO: for more robustness, we should check the ?XD/?XC tag to see if it's
    # 'EXD'/'EXC'. This requires that the prefix of the XD, XC is parsed,
    # which isn't the case as of yet (should be done in the ribxlib).

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
                measurement = self.save_measurement(item)
                if measurement is not None:
                    # Mark the locations with these flags for visualization.
                    location = measurement.location
                    if item.work_impossible:
                        location.work_impossible = True
                        location.save()
                    if item.new:
                        location.new = True
                        location.save()
                    measurements.append(measurement)
        return measurements
