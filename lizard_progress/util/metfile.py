from __future__ import unicode_literals, division
from __future__ import print_function, absolute_import

"""Utilities for met files."""

DWARSPROFIEL_MTYPE_SLUG = 'dwarsprofiel'

from lizard_progress import models


def generate_metfile(project, contractor, open_file):
    """We generate a metfile by:
    - Printing a trivial header
    - For each measurement currently in the database, find the file
      that measurement came from.
    - Write a trivial <reeks> line for that measurement
    - Copy the original measurement from the original file

    This way, we never omit data that was in the original file but may not be
    in our database."""

    write_trivial_header(open_file)
    for measurement in current_measurements(project, contractor):
        write_trivial_reeks(open_file, measurement)
        copy_measurement(open_file, measurement)


def write_trivial_header(open_file):
    open_file.write('<VERSIE>1.0</VERSIE>\n')


def current_measurements(project, contractor):
    return (measurement
            for measurement in models.Measurement.objects.filter(
            scheduled__project=project,
            scheduled__measurement_type__mtype__slug=DWARSPROFIEL_MTYPE_SLUG,
            scheduled__contractor=contractor).
            select_related())


def write_trivial_reeks(open_file, measurement):
    reeks = measurement.scheduled.location.location_code
    reeks = reeks.split('_')[0]

    # HACK
    # As of now, Realtech assumes that the Hydrovak-code is in this field.
    # We don't know the hydrovak code, and have no way to know it (in time,
    # the user protocol should be changed so that it is also in this field
    # when it is uploaded, and then we should store it along wit each
    # measurement).
    # For now, if the code ends with a '-' and a few digits, remove them.
    parts = reeks.split('-')
    if len(parts) > 1 and all(c.isdigit() for c in parts[-1]):
        reeks = '-'.join(parts[:-1])

    open_file.write('<REEKS>{0},{0},</REEKS>\n'.format(reeks))


def copy_measurement(open_file, measurement):
    metfile = measurement.abs_file_path
    location_code = measurement.scheduled.location.location_code

    open_file.write(get_profiel_from_metfile(location_code, metfile))


def profiel_line_generator(f, profiel_id):
    for line in f:
        line = line.decode('utf8')
        if line.startswith('<PROFIEL>{0}'.format(profiel_id)):
            yield line
            break

    for line in f:
        yield line
        if line.startswith('</PROFIEL>'):
            break


def get_profiel_from_metfile(profiel_id, metfile):
    # Open the metfile with 'rU' because of line ending confusions.
    # Because we build the rest of the file with our own line endings,
    # everything becomes mixed otherwise.
    return ''.join(profiel_line_generator(
            open(metfile, 'rU'), profiel_id))
