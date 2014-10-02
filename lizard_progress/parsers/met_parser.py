"""Parsers for files uploaded to the upload server. The parsers()
functions in hdsr.progress.py return the function in this file to
lizard-progress, which then calls them."""

import itertools
import logging
import math

from django.contrib.gis.geos import Point

from metfilelib.util import linear_algebra
from metfilelib.parser import parse_metfile

from lizard_progress import models
from lizard_progress import specifics
from lizard_progress.changerequests.models import Request

logger = logging.getLogger(__name__)


def pairs(iterable):
    iterable, helper_iter = itertools.tee(iterable)
    helper_iter.next()

    return itertools.izip(iterable, helper_iter)


class MetParser(specifics.ProgressParser):
    """Call the MET parser in metfilelib and save results in
    lizard-progress measurements."""

    # We use the FileReader class of metfilelib
    FILE_TYPE = specifics.FILE_READER

    def parse(self, check_only=False):
        self.error_config = self.activity.error_configuration()

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
                location = self.get_location(profile)
                if location is None:
                    continue

                m, created = models.Measurement.objects.get_or_create(
                    location=location)
                m.date = profile.date_measurement

                m.data = [{
                    'x': float(measurement.x),
                    'y': float(measurement.y),
                    'type': measurement.profile_point_type,
                    'top': measurement.z1,
                    'bottom': measurement.z2
                }
                    for measurement in profile.sorted_measurements
                ]

                if len(m.data) > 0:
                    # Use x, y of first point
                    m.record_location(Point(
                        m.data[0]['x'], m.data[0]['y'], srid=models.SRID))

                location.complete = True
                location.save()

                measurements.append(m)

        return self._parser_result(measurements)

    def check_content(self, parsed_metfile):
        for series in parsed_metfile.series:
            self.check_series(series)

    def check_series(self, series):
        for profile in series.profiles:
            self.check_profile(
                profile, series.id)

    def check_profile(self, profile, series_id):
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

        if profile.id.upper() != profile.id:
            self.record_error_code(
                profile.line_number, 'MET_PROFILE_ID_ALL_CAPS')

        if '_' not in profile.id:
            self.record_error_code(
                profile.line_number, 'MET_UNDERSCORE_IN_PROFILE_ID')
        else:
            parts = profile.id.split('_')
            first_part = parts[0]
            second_part = "_".join(parts[1:])

            if first_part != series_id:
                self.record_error_code(
                    profile.line_number, 'MET_SERIES_ID_IN_PROFILE_ID')

            if profile.description != "Profiel_{0}".format(second_part):
                self.record_error_code(
                    profile.line_number, 'MET_PROFILE_NUMBER_IN_DESC')

        max_z1 = max_z2 = None

        # Profile's start_x and start_y must be the coordinates of one
        # of the measurements
        if not any(
                measurement.x == profile.start_x
                and measurement.y == profile.start_y
                for measurement in profile.measurements):
            self.record_error_code(
                profile.line_number,
                'MET_PROF_COORDS_IN_MEASRMNTS')

        self.check_waternet_profile_point_types(profile)
        self.check_two_22_codes_with_z1z2_equal(profile)

        # Inside extent
        min_x = self.config_value('minimum_x_coordinate')
        max_x = self.config_value('maximum_x_coordinate')
        min_y = self.config_value('minimum_y_coordinate')
        max_y = self.config_value('maximum_y_coordinate')

        # Max mean distance
        if profile.line:
            distance = profile.line.length

            # If there is a line, there must also be a
            # water_measurements of at least length 2
            measurements = len(profile.water_measurements)

            mean_distance = distance / (measurements - 1)
            max_mean_distance = self.config_value(
                'maximum_mean_distance_between_points')
            if mean_distance > max_mean_distance:
                self.record_error_code(
                    profile.line_number,
                    'MET_MEAN_MEASUREMENT_DISTANCE',
                    mean_distance,
                    max_mean_distance)

        if not (min_x <= profile.start_x <= max_x):
            self.record_error_code(
                profile.line_number,
                'MET_INSIDE_EXTENT',
                'X', min_x, max_x)

        if not (min_y <= profile.start_y <= max_y):
            self.record_error_code(
                profile.line_number,
                'MET_INSIDE_EXTENT',
                'Y', min_y, max_y)

        if len(profile.measurements) >= 2:
            # Checks on the leftmost and rightmost measurement
            m1 = profile.measurements[0]
            m2 = profile.measurements[-1]

            baseline = profile.line
            if baseline is not None:
                width = baseline.length
                max_width = self.config_value('maximum_waterway_width')
                if width > max_width:
                    self.record_error_code(
                        profile.line_number,
                        'MET_WATERWAY_TOO_WIDE',
                        max_width)

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

            if m1.x != profile.start_x or m1.y != profile.start_y:
                self.record_error_code(
                    m1.line_number, "MET_XY_METING_IS_PROFILE")

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

            x_descending = None
            y_descending = None
            for m1, m2 in pairs(profile.measurements):
                # Points should be close to each other.
                max_measurement_distance = self.config_value(
                    'max_measurement_distance')
                if m1.point.distance(m2.point) > max_measurement_distance:
                    self.record_error_code(
                        m2.line_number,
                        'MET_DISTANCETOOLARGE',
                        distance=max_measurement_distance)

                # We don't know yet if x and y are descending or not
                if m1.x == m2.x or m1.y == m2.y:
                    self.record_error_code(
                        m2.line_number,
                        'MET_XY_STRICT_ASCDESC')
                    continue

                if x_descending is None:
                    x_descending = (m2.x < m1.x)
                elif x_descending != (m2.x < m1.x):
                    self.record_error_code(
                        m2.line_number,
                        'MET_XY_STRICT_ASCDESC')

                if y_descending is None:
                    y_descending = (m2.y < m1.y)
                elif y_descending != (m2.y < m1.y):
                    self.record_error_code(
                        m2.line_number,
                        'MET_XY_STRICT_ASCDESC')

                if m1.point.distance(m2.point) < 0.01:
                    self.record_error_code(
                        m2.line_number,
                        'MET_XY_ASCDESC_1CM')

            # XXX
            # For _Almere_, we do this check on the _sorted_ measurement lines.
            for m1, m2 in pairs(profile.sorted_measurements):
                # The difference in z values should not be too large (<= 1m)
                if abs(m1.z1 - m2.z1) > 1:
                    self.record_error_code(
                        m2.line_number,
                        'MET_Z1_DIFFERENCE_TOO_LARGE')
                if abs(m1.z2 - m2.z2) > 1:
                    self.record_error_code(
                        m2.line_number,
                        'MET_Z2_DIFFERENCE_TOO_LARGE')

        if len(profile.measurements) >= 1:
            for measurement in profile.measurements:
                self.check_measurement(
                    measurement, max_z1, max_z2, profile)

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

        if count_codes(measurements, '5') < 1:
            self.record_error_code(
                profile.line_number, 'MET_AT_LEAST_ONE_5_CODE')
            correct_so_far = False

        if count_codes(measurements, '6') < 1:
            self.record_error_code(
                profile.line_number, 'MET_AT_LEAST_ONE_6_CODE')
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
                self.record_error_code(
                    measurements[-1].line_number,
                    'MET_EXPECTED_CODE_2')
                return
        else:
            self.record_error_code(
                measurements[-1].line_number,
                'MET_EXPECTED_CODE_1')
            return

        # We now know the codes 1, 2, 22 and 7 have the right amounts, and
        # 1 and 2 occur at the right places. Now:
        # - in between 1 and 22, we may only see 99
        # - in between 22 and 7, we may only see 5 and 99
        # - in between 7 and 22, we may only see 6 and 99
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

        def check_codes(measurements, codes):
            for m in measurements:
                if m.profile_point_type not in codes:
                    self.record_error_code(
                        m.line_number,
                        'MET_WRONG_PROFILE_POINT_TYPE',
                        code=code)

        check_codes(measurements[1:indices_22[0]], ['99'])
        check_codes(measurements[indices_22[0] + 1:index_7[0]], ['5', '99'])
        check_codes(measurements[index_7[0] + 1:indices_22[1]], ['6', '99'])
        check_codes(measurements[indices_22[1] + 1:-1], ['99'])

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

    def check_measurement(self, measurement, max_z1, max_z2, profile):
        if measurement.z2 < measurement.z1:
            self.record_error_code(
                measurement.line_number,
                'MET_Z1GREATERTHANZ2')
        else:
            max_z1z2_difference = self.config_value('maximum_z1z2_difference')
            if (abs(measurement.z2 - measurement.z1) > max_z1z2_difference):
                self.record_error_code(
                    measurement.line_number,
                    'MET_DIFFERENCE_Z1Z2_MAX_1M',
                    max_z1z2_difference)

        lowest_allowed = self.config_value("lowest_z_value_allowed")
        if measurement.z1 < lowest_allowed or measurement.z2 < lowest_allowed:
            self.record_error_code(
                measurement.line_number,
                'MET_Z_TOO_LOW',
                lowest_allowed)

        if profile.waterlevel is not None:
            lowest_below_water_allowed = self.config_value(
                "lowest_below_water_allowed")
            lowest_allowed = lowest_below_water_allowed + profile.waterlevel
            if (measurement.z1 < lowest_allowed or
                    measurement.z2 < lowest_allowed):
                self.record_error_code(
                    measurement.line_number,
                    'MET_Z_TOO_LOW_BELOW_WATER',
                    lowest_allowed)

        if profile.line is not None and measurement.point is not None:
            distance = profile.line.distance(measurement.point)
            max_allowed_distance = self.config_value("max_distance_to_midline")
            if (distance > max_allowed_distance):
                self.record_error_code(
                    measurement.line_number,
                    'MET_DISTANCE_TO_MIDLINE',
                    distance, max_allowed_distance)

    def get_location(self, profile):
        try:
            point = Point(profile.start_x, profile.start_y)
            location = self.activity.get_or_create_location(
                location_code=profile.id, point=point)
            profile_point = profile.start_point

            location_point = linear_algebra.Point(
                x=location.the_geom.x, y=location.the_geom.y)
            distance = location_point.distance(profile_point)
            maxdistance = self.config_value('maximum_location_distance')
            if distance > maxdistance:
                self.record_error_code(
                    line_number=profile.line_number,
                    error_code="TOO_FAR_FROM_LOCATION",
                    location_id=profile.id,
                    x=location.the_geom.x, y=location.the_geom.y,
                    m=distance, maxm=maxdistance, recovery={
                        'request_type': Request.REQUEST_TYPE_MOVE_LOCATION,
                        'location_code': profile.id,
                        'x': profile.start_x,
                        'y': profile.start_y
                        })
            return location
        except models.Activity.NoLocationException:
            self.record_error_code(
                line_number=profile.line_number,
                error_code="NO_LOCATION",
                location_id=profile.id,
                recovery={
                    'request_type': Request.REQUEST_TYPE_NEW_LOCATION,
                    'location_code': profile.id,
                    'x': profile.start_x,
                    'y': profile.start_y
                })
            return None

    def record_error_code(self, line_number, error_code, *args, **kwargs):
        if error_code not in self.error_config:
            return

        recovery = kwargs.pop('recovery') if 'recovery' in kwargs else None

        self.record_error(
            line_number,
            *(models.ErrorMessage.format_code(error_code, *args, **kwargs)),
            recovery=recovery)

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
