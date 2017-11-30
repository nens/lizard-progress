# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

"""Parse an uploaded file, and if there were no errors, store the
information in the file and move it to a permanent spot."""

# Python 3 is coming
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import logging
import os
import shutil
import tempfile
import time

from django.db import transaction

from lizard_progress import models
from lizard_progress.changerequests.models import PossibleRequest
from lizard_progress import specifics

logger = logging.getLogger(__name__)


def process_uploaded_file(uploaded_file_id):
    try:
        uploaded_file = models.UploadedFile.objects.get(pk=uploaded_file_id)
        uploaded_file.wait_until_path_exists()
        process_capturing_errors(uploaded_file)
    except models.UploadedFile.DoesNotExist:
        # What can we do? Don't even have a good place to log errors
        logger.warn("uploaded_file_id not found in task: {0}".
                    format(uploaded_file_id))
    except models.UploadedFile.PathDoesNotExist:
        uploaded_file.ready = True
        uploaded_file.success = False
        uploaded_file.linelike = False
        uploaded_file.save()
        uploaded_file.uploadedfileerror_set.create(
            line=0,
            error_code="EXCEPTION",
            error_message="File lijkt verdwenen, onbekend probleem.")


def process_capturing_errors(uploaded_file):
    try:
        process(uploaded_file)
    except Exception as e:
        # Something went wrong. Record it as an error at line 0, what
        # else to do.
        logger.exception("Error processing uploaded file: %s.", e)
        uploaded_file.ready = True
        uploaded_file.success = False
        uploaded_file.linelike = False
        uploaded_file.save()
        # Give a generic error message for the user
        uploaded_file.uploadedfileerror_set.create(
            line=0,
            error_code="EXCEPTION",
            error_message=(
                "Onbekende fout opgetreden tijdens het verwerken van het "
                "bestand {0}".format(uploaded_file.filename))[:300])


def process(uploaded_file):
    filename = uploaded_file.filename

    # Since the latest change, where each measurement type has its own
    # upload button, there should always be a single possible parser per
    # uploaded file. However, we keep the functionality around of multiple
    # parsers being possible -- maybe we'll have a measurement type with
    # several parsers one day...
    possible_parsers = uploaded_file.activity.specifics().parsers(filename)

    for parser in possible_parsers:
        # Try_parser takes care of moving the file to its correct
        # destination if successful, and all database operations.
        success, errors, possible_requests = try_parser(uploaded_file, parser)

        if success:
            uploaded_file.ready = True
            uploaded_file.success = True
            uploaded_file.save()
            return
        if errors:
            uploaded_file.ready = True
            uploaded_file.success = False
            uploaded_file.save()

            # Record errors
            for error in errors:
                uploaded_file.uploadedfileerror_set.create(
                    line=error.line if uploaded_file.linelike else 0,
                    error_code=error.error_code or "UNKNOWNCODE",
                    error_message=error.error_message or "Unknown message")

            for possible_request in possible_requests:
                PossibleRequest.create_from_dict(
                    uploaded_file, possible_request)

            return

        # If no success and no errors, try the next parser.

    # Error: unknown file type, no parser was suitable.
    uploaded_file.ready = True
    uploaded_file.success = False
    uploaded_file.save()
    uploaded_file.uploadedfileerror_set.create(
        line=0,
        error_code="FILETYPE",
        error_message=(
            "Onbekend filetype."))


def try_parser(uploaded_file, parser):
    """Tries a particular parser. Wraps everything in a database
    transaction so that nothing is changed in the database in case
    of an error message. Moves the file to the current location
    and updates its taken measurements with the new filename in
    case of success."""

    errors = []
    possible_requests = []

    # We use transaction.commit_on_success to control our
    # transactions, so that if any unexpected exceptions happen in
    # the code we call, nothing will be saved to the
    # database. This also means that we have to raise an exception
    # in case we want to rollback the transaction for more normal
    # reasons (in case some error was found in the file).
    class DummyException(Exception):
        pass

    try:
        with transaction.commit_on_success():
            # Call the parser.
            parseresult = call_parser(uploaded_file, parser)
            if (parseresult.success and hasattr(parseresult, 'measurements')
                    and parseresult.measurements):
                # Move the file.
                target_path = path_for_uploaded_file(
                    uploaded_file.activity,
                    os.path.basename(uploaded_file.filename))

                shutil.move(uploaded_file.abs_file_path, target_path)

                models.AcceptedFile.create_from_path(
                    activity=uploaded_file.activity,
                    rel_file_path=directories.relative(target_path))

                # Update measurements and locations.
                for m in parseresult.measurements:
                    m.rel_file_path = target_path
                    m.save()
                    location = m.location
                    location.one_measurement_uploaded = True
                    location.measured_date = location.latest_measurement_date()
                    location.save()

                # Log success
                uploaded_file.log_success(parseresult.measurements)

                return True, [], []

            elif parseresult.success:
                # Success, but no results.  Don't count this as
                # success, so that other parsers may be tried.

                # Prevent database change.
                raise DummyException()
            else:
                # Unsuccess. Were there errors? Then set
                # them.

                # New style errors (possibly more than one)
                if parseresult.errors:
                    errors = parseresult.errors
                    possible_requests = parseresult.possible_requests
                # Old style (only one)
                elif parseresult.error:
                    errors = [
                        specifics.Error(
                            line=0,
                            error_code='NONE',
                            error_message=parseresult.error)
                        ]

                # We raise a dummy exception so that
                # commit_on_success doesn't commit whatever
                # was done to our database in the meantime.
                raise DummyException()
    except DummyException:
        pass
    return False, errors, possible_requests


def call_parser(uploaded_file, parser):
    """Actually call the parser. Open files. Return result."""

    parser_instance = specifics.parser_factory(
        parser,
        uploaded_file.activity,
        uploaded_file.abs_file_path)

    parseresult = parser_instance.parse()
    return parseresult


def path_for_uploaded_file(activity, filename):
    """Create dirname based on project etc. Guaranteed not to
    exist yet at the time of checking."""

    dirname = activity.abs_upload_directory()

    # Create a directory using mkdtemp, with current date and time as
    # prefix so that they sort chronologically.
    return os.path.join(
        tempfile.mkdtemp(prefix=time.strftime('%Y%m%d%H%M%S'), dir=dirname),
        filename)
