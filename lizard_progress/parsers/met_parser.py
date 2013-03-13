"""Parsers for files uploaded to the upload server. The parsers()
functions in hdsr.progress.py return the function in this file to
lizard-progress, which then calls them."""

import logging
import math

from django.contrib.gis.geos import Point

from metfilelib.parser import parse_metfile

from lizard_progress import models
from lizard_progress import specifics
from lizard_progress import errors

logger = logging.getLogger(__name__)


class MetProfiel(object):
    """Class holding the results of parsing a <profiel> METfile
    section."""
    def __init__(self, location, scheduled, date, measurements):
        self.location = location
        self.scheduled = scheduled
        self.date = date
        self.measurements = measurements

    def save(self):
        """Save the measurements represented by this object into the
        database."""

        # For this measurement type there is a single
        # Measurement per ScheduledMeasurement, we can
        # use get.
        m, _ = (models.Measurement.objects.
                get_or_create(scheduled=self.scheduled))
        m.data = self.measurements
        m.date = self.date
        # Use xy of the first point
        m.the_geom = Point(self.measurements[0]['x'],
                           self.measurements[0]['y'],
                           srid=models.SRID)
        m.save()

        self.scheduled.complete = True
        self.scheduled.save()

        return m


class MetParser(specifics.ProgressParser):
    """Call the MET parser in metfilelib and save results in
    lizard-progress measurements."""

    # We use the FileReader class of metfilelib
    FILE_TYPE = specifics.FILE_READER

    def parse(self, check_only=False):
        self.error_config = (
            errors.ErrorConfiguration(self.project, self.mtype()))

        parsed_metfile = parse_metfile(self.file_object)

        if parsed_metfile is None:
            # File is not a MET file. Returned empty successful result.
            return specifics.SuccessfulParserResult(())

        measurements = []

        if self.file_object.errors:
            # There were errors, record them
            for error in self.file_object.errors:
                self.record_error(
                    error.line, error.error_code, error.error_message)

        self.check_content(parsed_metfile)

        # Save the measured profiles.
        for series in parsed_metfile.series:
            for profile in series.profiles:
                scheduled_measurement = (
                    self.get_scheduled_measurement(profile))
                if scheduled_measurement is None:
                    continue

                m, created = models.Measurement.objects.get_or_create(
                    scheduled=scheduled_measurement)
                m.date = profile.date_measurement
                m.data = [{
                        'x': float(measurement.x),
                        'y': float(measurement.y),
                        'type': measurement.profile_point_type,
                        'top': measurement.z1,
                        'bottom': measurement.z2
                        }
                          for measurement in profile.measurements
                          ]

                # Use x, y of first point
                m.the_geom = Point(
                    m.data[0]['x'], m.data[0]['y'], srid=models.SRID)
                m.save()

                scheduled_measurement.complete = True
                scheduled_measurement.save()

                measurements.append(m)

        return self._parser_result(measurements)

    def check_content(self, parsed_metfile):
        for series in parsed_metfile.series:
            self.check_series(series)

    def check_series(self, series):
        for profile in series.profiles:
            self.check_profile(profile)

    def check_profile(self, profile):
        if profile.level_type != 'NAP':
            self.record_error_code(
                profile.line_number, 'MET_NAP')

        if profile.coordinate_type != 'ABS':
            self.record_error_code(
                profile.line_number, 'MET_ABS')

        if profile.level_value != 0.0:
            self.record_error_code(
                profile.line_number, 'MET_PEILWAARDENUL')

        if profile.number_of_z_values != 2:
            self.record_error_code(
                profile.line_number, 'MET_TWOZVALUES')

        if profile.profile_type_placing != 'XY':
            self.record_error_code(
                profile.line_number, 'MET_PROFILETYPEPLACING_XY')

        if len(profile.measurements) < 2:
            self.record_error_code(
                profile.line_number, 'MET_2MEASUREMENTS')

        max_z1 = max_z2 = None

        if len(profile.measurements) >= 2:
            m1 = profile.measurements[0]
            m2 = profile.measurements[-1]
            if m1.z1 != m2.z1 or m1.z2 != m2.z2:
                self.record_error_code(
                    profile.line_number, 'MET_LEFTRIGHTEQUAL')

            if m1.x == m2.x and m1.y == m2.y:
                self.record_error_code(
                    profile.line_number, 'MET_LEFTRIGHTXY')

            if (m1.profile_point_type != '22' or
                m2.profile_point_type != '22'):
                self.record_error_code(
                    profile.line_number, 'MET_22OUTSIDE')
            else:
                if m1.profile_point_type == '22':
                    max_z1 = m1.z1
                    max_z2 = m1.z2
                else:
                    max_z1 = m2.z1
                    max_z2 = m2.z2

            for measurement in profile.measurements[1:-1]:
                if max_z1 is not None and measurement.z1 > max_z1:
                    self.record_error_code(
                        measurement.line_number, 'MET_Z1TOOHIGH')
                if max_z2 is not None and measurement.z2 > max_z2:
                    self.record_error_code(
                        measurement.line_number, 'MET_Z2TOOHIGH')

                if measurement.profile_point_type != '99':
                    self.record_error_code(
                        measurement.line_number, 'MET_99INSIDE')

            # Points should be close to each other. We set the limit
            # at 5m because of measurement inaccuracy.
            limit = 5

            distances = [
                (self.distance(
                    profile.measurements[i], profile.measurements[i + 1]),
                 profile.measurements[i].line_number)
                for i in range(0, len(profile.measurements) - 1)]
            for distance, line_number in distances:
                if distance > limit:
                    self.record_error_code(
                        line_number,
                        'MET_DISTANCETOOLARGE', distance=limit)

        if len(profile.measurements) >= 1:
            for measurement in profile.measurements:
                self.check_measurement(measurement, max_z1, max_z2)

    def check_measurement(self, measurement, max_z1, max_z2):
        if measurement.z2 < measurement.z1:
            self.record_error_code(
                measurement.line_number,
                'MET_Z1GREATERTHANZ2')

    def get_scheduled_measurement(self, profile):
        try:
            location = models.Location.objects.get(
                project=self.project,
                location_code=profile.id)
        except models.Location.DoesNotExist:
            self.record_error_code(
                line_number=profile.line_number,
                error_code="NO_LOCATION",
                location_id=profile.id)
            return None

        try:
            scheduled_measurement = (
                models.ScheduledMeasurement.objects.
                get(project=self.project,
                    contractor=self.contractor,
                    location=location,
                    measurement_type=self.mtype()))
        except models.ScheduledMeasurement.DoesNotExist:
            self.record_error_code(
                line_number=profile.line_number,
                error_code="NO_SCHEDULED")
            return None

        return scheduled_measurement

    def mtype(self):
        """Return the measurement_type instance for dwarsprofielen"""
        try:
            return models.MeasurementType.objects.get(
                project=self.project,
                mtype__slug='dwarsprofiel')
        except models.MeasurementType.DoesNotExist:
            self.record_error(
                0, "MET_NOMEASUREMENTTYPE",
                "Measurement type 'dwarsprofiel' niet geconfigureerd.")

    def record_error_code(self, line_number, error_code, **kwargs):
        logger.warn("Recording error at {0}, error_code {1}"
                    .format(line_number, error_code))
        if error_code not in self.error_config:
            return

        self.record_error(
            line_number,
            *(models.ErrorMessage.format_code(error_code, **kwargs)))

    def distance(self, m1, m2):
        try:
            # X and Y are in RD
            x1 = float(m1.x)
            y1 = float(m1.y)
            x2 = float(m2.x)
            y2 = float(m2.y)

            return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        except ValueError:
            return 0
