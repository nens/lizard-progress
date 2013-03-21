"""Parsers for files uploaded to the upload server. The parsers()
functions in hdsr.progress.py return the function in this file to
lizard-progress, which then calls them."""

# Codes not in migrations yet:

# MET_ONE_1_CODE {0}
# MET_ONE_2_CODE {0}
# MET_TWO_22_CODES {0}
# MET_ONE_7_CODE {0}
# MET_EXPECTED_CODE_2
# MET_EXPECTED_CODE_1
# MET_EXPECTED_CODE_1_OR_2
# MET_CODE_7_IN_BETWEEN_22
# MET_WRONG_PROFILE_POINT_TYPE

import logging
import math

from django.contrib.gis.geos import Point

from metfilelib.parser import parse_metfile

from lizard_progress import models
from lizard_progress import specifics
from lizard_progress import errors

logger = logging.getLogger(__name__)


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

                if len(m.data) > 0:
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

        self.check_waternet_profile_point_types(profile)
        self.check_two_22_codes_with_z1z2_equal(profile)

        if len(profile.measurements) >= 2:
            # Checks on the leftmost and rightmost measurement
            m1 = profile.measurements[0]
            m2 = profile.measurements[-1]

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

    def check_waternet_profile_point_types(self, profile):
        ## For Waternet, code checks are pretty involved:
        # Exactly one code '1', one code '2', two codes '22',
        # one code '7', codes '5' in between 22 and 7, codes '6' in
        # between 7 and 22.
        def count_codes(measurements, code):
            return len([m for m in measurements
                        if m.profile_point_type == code])

        measurements = profile.measurements

        correct_so_far = True

        for code, amount, error_code in (
            ('1', 1, 'MET_ONE_1_CODE'),
            ('2', 1, 'MET_ONE_2_CODE'),
            ('22', 2, 'MET_TWO_22_CODES'),
            ('7', 1, 'MET_ONE_7_CODE')):
            found_amount = count_codes(measurements, code)
            if found_amount != amount:
                self.record_error_code(
                    profile.line_number, error_code, found_amount)
                correct_so_far = False

        if not correct_so_far:
            return

        # Now check if the 1 and 2 codes are in the correct spot
        # We know there are more than 2 measurements or the above would
        # never have been successful.
        if measurements[0].profile_point_type == '1':
            # Then last must be 2
            if measurements[-1].profile_point_type == '2':
                # Okay
                pass
            else:
                self.record_error(
                    measurements[-1].line_number,
                    'MET_EXPECTED_CODE_2')
                success_so_far = False
        else:
            if measurements[0].profile_point_type == '2':
                # Then last must be 1
                if measurements.profile_point_type == '1':
                    # Okay. Apparently they're the other way around, so we
                    # reverse the list for the last check.
                    measurements = list(reversed(measurements))
                else:
                    self.record_error(
                        measurements[-1].line_number,
                        'MET_EXPECTED_CODE_1')
                    success_so_far = False
            else:
                self.record_error(measurements[0].line_number,
                                  'MET_EXPECTED_CODE_1_OR_2')
                success_so_far = False

        if not success_so_far:
            return

        # We now know the codes 1, 2, 22 and 7 have the right amounts, and
        # 1 and 2 occur at the right places. Now:
        # - in between 1 and 22, we may only see 99
        # - in between 22 and 7, we may only see 5
        # - in between 7 and 22, we may only see 6
        # - in between 22 and 2, we may only see 99
        indices_22 = [i for i, m in enumerate(measurements)
                      if m.profile_point_type == '22']
        index_7 = [i for i, m in enumerate(measurements)
                   if m.profile_point_type == '7']

        if not (indices_22[0] < index_7[0] < indices_22[1]):
            self.record_error_code(
                measurements[index_7[0]].line_number,
                'MET_CODE_7_IN_BETWEEN_22')
            return

        def check_codes(measurements, code):
            for m in measurements:
                if m.profile_point_type != code:
                    self.record_error_code(
                        m.line_number,
                        'MET_WRONG_PROFILE_POINT_TYPE',
                        code=code)

        check_codes(measurements[1:indices_22[0]], '99')
        check_codes(measurements[indices_22[0] + 1:index_7[0]], '5')
        check_codes(measurements[index_7[0] + 1:indices_22[1]], '6')
        check_codes(measurements[indices_22[1] + 1:-1], '99')

    def check_two_22_codes_with_z1z2_equal(self, profile):
        if len(profile.measurements) >= 2:
            # Checks on both 22 codes.
            ms = [m for m in profile.measurements
                  if m.profile_point_type == '22']

            if len(ms) != 2:
                # This error is already recorded in
                # check_waternet_profile_point_types
                #self.record_error_code(
                #    profile.line_number, 'MET_TWO_22_CODES', len(ms))
                pass
            else:
                if ms[0].z1 != ms[1].z1 or ms[0].z2 != ms[1].z2:
                    self.record_error_code(
                        profile.line_number, 'MET_LEFTRIGHTEQUAL')

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
            if "NO_LOCATION" in self.error_config:
                self.record_error_code(
                    line_number=profile.line_number,
                    error_code="NO_LOCATION",
                    location_id=profile.id)
                return None
            else:
                location = models.Location.objects.create(
                    project=self.project,
                    location_code=profile.id,
                    the_geom=Point(profile.start_x, profile.start_y))
        try:
            scheduled_measurement = (
                models.ScheduledMeasurement.objects.
                get(project=self.project,
                    contractor=self.contractor,
                    location=location,
                    measurement_type=self.mtype()))
        except models.ScheduledMeasurement.DoesNotExist:
            if "NO_SCHEDULED" in self.error_config:
                self.record_error_code(
                    line_number=profile.line_number,
                    error_code="NO_SCHEDULED")
                return None
            else:
                scheduled_measurement = (
                    models.ScheduledMeasurement.objects.create(
                        project=self.project,
                        contractor=self.contractor,
                        location=location,
                        measurement_type=self.mtype()))

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

    def record_error_code(self, line_number, error_code, *args, **kwargs):
        if error_code not in self.error_config:
            return

        self.record_error(
            line_number,
            *(models.ErrorMessage.format_code(error_code, *args, **kwargs)))

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
