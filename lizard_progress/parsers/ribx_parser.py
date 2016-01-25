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


def _get_record_id(filename):
    # In this block we're trying to get the id of the file we just
    # uploaded, which is kinda elaborate... First we need to get the
    # list of all ids, then select the ids with the right filename,
    # and then select the newest.
    # TODO: this method is very error prone, and should be removed
    # as soon as the HTTP API is able to return the record id immediately.
    _id = None
    r_getids = requests.get(settings.GWSW_GETIDS_URL)
    if r_getids.ok:
        try:
            d = json.loads(r_getids.text)
            all_ids = d['ids']
        except ValueError:
            logger.exception("Could not get IDs because invalid JSON: %s",
                             r_getids.url)
        except KeyError:
            logger.exception("No 'ids' key in the JSON at this url: %s",
                             r_getids.url)
        else:
            possible_ids = [x for x in all_ids if
                            x['filename'] == filename]
            try:
                # We assume the highest id is the newest, and the one we want.
                newest = max(possible_ids, key=lambda x: x['id'])
            except (ValueError, KeyError):
                logger.exception("No ids or corrupt data: %s", possible_ids)
            else:
                _id = newest['id']
    return _id


def get_record_id(filename, retries=10):
    """Get the record id of the uploaded file, which is needed for retrieving
    additional info about the file.

    Args:
        filename: filename of the uploaded file
        retries: max number of retries to the HTTP API
    """
    tries = 1 + retries  # We try and retry, just like in life.
    record_id = None
    for i in range(tries):
        logger.debug("get_record_id try number %s", i)
        record_id = _get_record_id(filename)
        if not record_id:
            time.sleep(i**2 + 1)
        else:
            logger.debug("get_record_id succesful")
            break
    return record_id


def _get_log_content(record_id):
    r_getlog = requests.get(settings.GWSW_GETLOG_URL % record_id)
    log_content = None
    if r_getlog.ok:
        try:
            j = json.loads(r_getlog.text)
        except ValueError:
            logger.exception("Invalid JSON, url: %s", r_getlog.url)
        else:
            try:
                log_content = j['logcontent']
            except KeyError:
                logger.exception(
                    "No 'logcontent' key in the JSON at this url: %s",
                    r_getlog.url)
    return log_content


def get_log_content(filename, retries=10):
    """Get the log from an uploaded ribx file.

    Args:
        filename: name of the file
        retries: max number of retries to the HTTP API
    """
    tries = 1 + retries  # We try and retry, just like in life.
    log_content = None
    for i in range(tries):
        logger.debug("get_log_content try number %s", i)
        log_content = _get_log_content(filename)
        # If the ribx file has not yet been processed you will get a
        # log_content with the value ['']. The join operation will check if it
        # contains only blank values.
        if not log_content or not ''.join(log_content):
            time.sleep(2*i**2 + 1)
        else:
            logger.debug("get_log_content succesful")
            break
    return log_content


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
            else:
                line_no = None
                try:
                    line_no = int(l.strip()[6:-1])
                except ValueError:
                    logger.exception("Can't convert line number: %s", l)
                else:
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
    """
    with reopen_file(file_obj, 'rb') as f:
        logger.info("Uploading file to RIONED GWSW API...")
        r_upload = requests.post(settings.GWSW_UPLOAD_URL,
                                 files={file_obj.name: f})
    logger.info("GWSW Upload response: %s", r_upload.text)
    errors = []
    if r_upload.ok:
        filepath = os.path.abspath(f.name)
        filename = os.path.basename(filepath)
        record_id = get_record_id(filename, retries=10)
        if record_id is not None:
            log_content = get_log_content(record_id, retries=10)
            if log_content:
                errors = parse_log_content(log_content)
    else:
        logger.error("Can't make request to %s", r_upload.url)
    return errors


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

        gwsw_errors = check_gwsw(self.file_object)
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
