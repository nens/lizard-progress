"""Parsers for files uploaded to the upload server. The parsers()
functions in hdsr.progress.py return the function in this file to
lizard-progress, which then calls them."""

import logging

from django.contrib.gis.geos import Point

from metfilelib.parser import parse_metfile

from lizard_progress import models
from lizard_progress import specifics

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
        else:
            # Save the measured profiles.

            for series in parsed_metfile.series:
                for profile in series.profiles:
                    try:
                        location = models.Location.objects.get(
                            project=self.project,
                            location_code=profile.id)
                    except models.Location.DoesNotExist:
                        self.record_error_code(
                            line_number=profile.line_number,
                            error_code="NO_LOCATION",
                            location_id=profile.id)
                        continue

                    try:
                        scheduled_measurement = (
                            models.ScheduledMeasurement.objects.
                            get(project=self.project,
                                contractor=self.contractor,
                                location=location,
                                measurement_type=self.mtype()))
                    except models.ScheduledMeasurement.DoesNotExist:
                        self.record_error(
                            line_number=profile.line_number,
                            error_code="NO_SCHEDUL",
                            error_message=(
                                "Geen dwarsprofiel ingepland, project={0}, contractor={1}, location={2}, measurement_type={3}"
                                .format(self.project.id, self.contractor.id, location.id, self.mtype())))
                        continue

                    m, created = models.Measurement.objects.get_or_create(
                        scheduled=scheduled_measurement)
                    m.date = profile.date_measurement
                    m.data = [
                        {
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
        self.record_error(
            line_number,
            *(models.ErrorMessage.format_code(error_code, **kwargs)))
