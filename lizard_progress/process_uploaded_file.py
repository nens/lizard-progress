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
import time
import traceback

from django.db import transaction
from django.conf import settings

from lizard_progress import models
from lizard_progress import specifics
from lizard_progress.tools import unique_filename

logger = logging.getLogger(__name__)


def document_root():
    """Get the document root for uploaded files as an absolute path.
    If LIZARD_PROGRESS_ROOT is given in settings, return that,
    otherwise the directory var/lizard_progress/ under BUILDOUT_DIR.
    """

    root = getattr(settings, 'LIZARD_PROGRESS_ROOT', None)
    if root is None:
        root = os.path.join(settings.BUILDOUT_DIR,
                            'var', 'lizard_progress')
    return root


def make_uploaded_file_path(root, project, contractor,
                            measurement_type, filename):
    """Gives the path to some uploaded file, which depends on the
    project it is for, the contractor that uploaded it and the
    measurement type that got its data from this file.

    Project, contractor, measurement_type can each be either a
    model instance of that type or a string containing the slug
    of one.

    Can be used both for absolute file paths (pass in document_root()
    as root) or for URLs that will be passed to Nginx for X-Sendfile
    (uses /protected/ as the root).

    External URLs should use a reverse() call to the
    lizard_progress_filedownload view instead of this function."""

    if isinstance(project, models.Project):
        project = project.slug
    if isinstance(contractor, models.Contractor):
        contractor = contractor.slug
    if isinstance(measurement_type, models.MeasurementType):
        measurement_type = measurement_type.slug

    return os.path.join(root,
                        project,
                        contractor,
                        measurement_type,
                        os.path.basename(filename))


def process_uploaded_file(uploaded_file_id):
    try:
        uploaded_file = models.UploadedFile.objects.get(pk=uploaded_file_id)
        process_capturing_errors(uploaded_file)
    except models.UploadedFile.DoesNotExist:
        # What can we do? Don't even have a good place to log errors
        logger.warn("uploaded_file_id not found in task: {0}".
                    format(uploaded_file_id))


def process_capturing_errors(uploaded_file):
    try:
        process(uploaded_file)
    except Exception as e:
        # Something went wrong. Record it as an error at line 0, what
        # else to do.
        print(traceback.format_exc())
        uploaded_file.ready = True
        uploaded_file.success = False
        uploaded_file.linelike = False
        uploaded_file.save()
        uploaded_file.uploadedfileerror_set.create(
            line=0,
            error_code="EXCEPTION",
            error_message=(
                "Fout tijdens verwerken van de file: {0}, {1}"
                .format(e, traceback.format_exc()))[:300])


def process(uploaded_file):
    filename = uploaded_file.filename
    possible_parsers = uploaded_file.project.specifics().parsers(filename)

    for parser in possible_parsers:
        # Try_parser takes care of moving the file to its correct
        # destination if successful, and all database operations.
        success, errors = try_parser(uploaded_file, parser)

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
                    error_message=error.error_message)

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

    try:
        # We use transaction.commit_on_success to control our
        # transactions, so that if any unexpected exceptions happen in
        # the code we call, nothing will be saved to the
        # database. This also means that we have to raise an exception
        # in case we want to rollback the transaction for more normal
        # reasons (in case some error was found in the file).
        class DummyException(Exception):
            pass

        with transaction.commit_on_success():
            # Call the parser.
            parseresult = call_parser(uploaded_file, parser)

            if (parseresult.success
                and hasattr(parseresult, 'measurements')
                and parseresult.measurements):
                # Get mtype from the parser result, for use in pathname
                mtype = (parseresult.measurements[0].
                         scheduled.measurement_type)

                # Move the file.
                target_path = path_for_uploaded_file(uploaded_file, mtype)
                shutil.move(uploaded_file.path, target_path)

                # Update measurements.
                for m in parseresult.measurements:
                    m.filename = target_path
                    m.save()

                return True, []

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

    return False, errors


def call_parser(uploaded_file, parser):
    """Actually call the parser. Open files. Return result."""

    parser_instance = specifics.parser_factory(
        parser,
        uploaded_file.project,
        uploaded_file.contractor,
        uploaded_file.path)
    parseresult = parser_instance.parse()
    return parseresult


def path_for_uploaded_file(uploaded_file, measurement_type):
    """Create dirname based on project etc. Guaranteed not to
    exist yet at the time of checking."""

    dirname = os.path.dirname(make_uploaded_file_path(
            document_root(),
            uploaded_file.project, uploaded_file.contractor,
            measurement_type, 'dummy'))

    # Create directory if does not exist yet
    if not os.path.exists(dirname):
        os.makedirs(dirname)

    # Figure out a filename that doesn't exist yet
    orig_filename = os.path.basename(uploaded_file.filename)
    seq = 0
    while True:
        new_filename = unique_filename(orig_filename, seq)
        if not os.path.exists(os.path.join(dirname, new_filename)):
            break
        # Increase sequence number if filename exists
        seq += 1

    return os.path.join(dirname, new_filename)
