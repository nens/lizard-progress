"""Parsers for files uploaded to the upload server. The parsers()
functions in hdsr.progress.py return the function in this file to
lizard-progress, which then calls them."""

from datetime import datetime
from math import sqrt
import logging

from django.contrib.gis.geos import Point

from lizard_map.coordinates import wgs84_to_rd
from lizard_progress.models import Location
from lizard_progress.models import Measurement
from lizard_progress.models import MeasurementType
from lizard_progress.models import SRID
from lizard_progress.models import ScheduledMeasurement
from lizard_progress.specifics import ProgressParser
from lizard_progress.specifics import UnSuccessfulParserResult

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
        m, _ = (Measurement.objects.
                get_or_create(scheduled=self.scheduled))
        m.data = self.measurements
        m.date = self.date
        # Use xy of the first point
        m.the_geom = Point(self.measurements[0]['x'],
                           self.measurements[0]['y'],
                           srid=SRID)
        m.save()

        self.scheduled.complete = True
        self.scheduled.save()

        return m


class MetParser(ProgressParser):
    """Parser for MET files. The current implementation mixes
    MET-standard checks and HDSR-specific checks and should be
    refactored at some point."""

    ERRORS = {
        'geen_mtype': ("Metingtype 'dwarsprofiel' niet gevonden. Dit is "
                       "een fout in de configuratie van de site."),
        'id_onbekend': "ProfielIdentificatie onbekend: %s",
        'not_scheduled': "Meting met id %s en type %s was niet gepland.",
        'z2>z1': "ID %s: Z2-waarde (%f) > Z1-waarde (%f)",
        'minstens2': "Niet minstens 2 metingen bij ID %s.",
        'linksrechts': "Bij ID %s zijn links en rechts niet gelijk.",
        'zelfdexy': "Bij ID %s hebben X en Y links en rechts dezelfde waarde.",
        'float': "Kon '%s' niet inlezen als getal.",
        'nap': ('Het 5e element van de <PROFIEL> regel '
                '(PeilType) moet "NAP" zijn.'),
        'abs': ('Het 6e element van de <PROFIEL> regel (CoordinaatType) '
                'moet "ABS" zijn.'),
        'peilwaarde': ('Het 4e element van de <PROFIEL> regel '
                       '(Peilwaarde) moet 0 zijn.'),
        'zwaarden': ('Het 7e element van de <PROFIEL> regel (aantal '
                     'Z waarden) moet gelijk zijn aan 2.'),
        'xy': ('Het 8e element van de <PROFIEL> regel (ProfielTypePlaatsing)'
               ' moet gelijk zijn aan "XY".'),
        'datum': 'Datum "%s" is niet in het vereiste formaat JJJJMMDD.',
        'tehoog': ("Bij locatie %s is de waarde %.3f hoger "
                   "dan de oever (%.3f)."),
        'toofar': ("Een punt op locatie %s ligt op %.1fm afstand "
                   "van het punt ernaast."),
        'parts': ("<PROFIEL> regel heeft te weinig onderdelen."),
        '<meting>': (
            "<METING> regel moet beginnen met &lt;METING> en "
            "eindigen met &lt;/METING>."),
        '2299': ("Metingtype moet 22 of 99 zijn, maar was '%s'."),
        'not6': (
            "Een <METING> regel moet 6 waarden bevatten, maar had er %d."),
        }

    def parse(self, check_only=False):
        try:
            self.mtype = MeasurementType.objects.get(
                project=self.project,
                mtype__slug='dwarsprofiel')
        except MeasurementType.DoesNotExist:
            return self.error('geen_mtype')

        result_measurements = []

        with self.lookahead() as la:
            while not la.eof():
                if la.line.startswith('<PROFIEL>'):
                    profiel, error = self.parse_profiel(la)
                    if error:
                        return error

                    if not check_only:
                        result_measurements.append(profiel.save())
                else:
                    la.next()

        return self.success(result_measurements)

    def parse_profiel(self, la):
        """Parse a <profiel> section. Return a tuple consisting of a
        MetProfiel instance and an error, if any."""

        (profielid, date), error = (
            self.parse_profiel_line(la.line))
        if error:
            return None, error

        try:
            location = Location.objects.get(
                project=self.project,
                location_code=profielid)
        except Location.DoesNotExist:
            return None, self.error('id_onbekend', profielid)

        try:
            scheduled_measurement = (
                ScheduledMeasurement.objects.
                get(project=self.project,
                    contractor=self.contractor,
                    location=location,
                    measurement_type=self.mtype))
        except ScheduledMeasurement.DoesNotExist:
            return None, self.error(
                'not_scheduled', profielid, str(self.mtype))

        la.next()

        measurements = []
        while not la.eof() and la.line.startswith('<METING>'):
            measurement, error = self.parse_meting_line(la.line, location)
            if error:
                return None, error
            if measurement:
                measurements.append(measurement)
            la.next()

        error = self.check_all_measurements(measurements, location)
        if error:
            return None, error

        return (
            MetProfiel(location, scheduled_measurement, date, measurements),
            None)

    def parse_meting_line(self, line, location):
        """Parse a <meting> line in a docfile. Location is given so it
        can be used in error messages."""

        line = line.strip()
        if not line.startswith('<METING>') or not line.endswith('</METING>'):
            return None, self.error('<meting>')
        line = line[len('<METING>'):-len('</METING>')]

        values = line.split(',')

        if len(values) != 6:
            return None, self.error("not6", len(values))

        metingtype = values[0].strip()
        if not metingtype in ('22', '99'):
            return None, self.error('2299', metingtype)
        else:
            # We could keep it a string, but chose to make it an int
            # at first and now there's no real reason to change it
            # back to string.
            metingtype = int(metingtype)

        try:
            x = float(values[2])
        except ValueError:
            return None, self.error('float', values[2])
        try:
            y = float(values[3])
        except ValueError:
            return None, self.error('float', values[3])

        try:
            bottom = float(values[4])  # Z1-waarde
        except ValueError:
            return None, self.error('float', values[4])
        try:
            top = float(values[5])  # Z2-waarde
        except ValueError:
            return None, self.error('float', values[5])

        if not bottom <= top:
            return None, self.error(
                'z2>z1', location.location_code, bottom, top)

        return {
            'x': x,
            'y': y,
            'type': metingtype,
            'top': top,
            'bottom': bottom
            }, None  # No errors

    def parse_profiel_line(self, line):
        """Split the <profiel> line into parts and check them."""

        line = line.strip()

        noresult = (None, None)

        parts = line[len('<PROFIEL>'):].split(',')
        if len(parts) != 11:
            return noresult, self.error('parts')

        profielid = parts[0].strip()

        try:
            peilwaarde = float(parts[3])
        except ValueError:
            peilwaarde = -1
        if peilwaarde != 0:
            return noresult, self.error('peilwaarde')

        if parts[4] != 'NAP':
            return noresult, self.error('nap')
        if parts[5] != 'ABS':
            return noresult, self.error('abs')
        if parts[6] != '2':
            return noresult, self.error('zwaarden')
        if parts[7] != 'XY':
            return noresult, self.error('xy')

        try:
            date = datetime.strptime(parts[2].strip(), '%Y%m%d')
        except ValueError:
            return noresult, self.error('datum', parts[2])

        try:
            float(parts[8])
        except ValueError:
            return noresult, self.error('float', parts[8])
        try:
            float(parts[9])
        except ValueError:
            return noresult, self.error('float', parts[9])

        return ((profielid, date), None)

    def check_all_measurements(self, measurements, location):
        """Checks that apply to the whole set of measurements, not
        just a single line. The 'location' argument is used in error
        messages."""

        if not measurements or len(measurements) < 2:
            return self.error('minstens2', location.location_code,)

        first = measurements[0]
        last = measurements[-1]

        # First and last should have type 22 (HDSR specific)
        if first['type'] != 22 or last['type'] != 22:
            return UnSuccessfulParserResult(
         "Bij ID %s is het metingtype van de eerste of laatste meting niet 22."
                % (location.location_code,))

        # And in between should be 99 (HDSR specific)
        if not all(measurement['type'] == 99
                   for measurement in measurements[1:-1]):
            return UnSuccessfulParserResult(
         "Bij ID %s zijn de metingtypes tussen de oevers in niet alle 99."
                % (location.location_code,))

        if first['top'] != first['bottom']:
            return UnSuccessfulParserResult(
                ("Bij ID %s zijn links de top en bottom " +
                 "waarden niet gelijk.") % (location.location_code,))

        if last['top'] != last['bottom']:
            return UnSuccessfulParserResult(
                ("Bij ID %s zijn rechts de top en bottom " +
                 "waarden niet gelijk.") % (location.location_code,))

        if first['top'] != last['top']:
            return self.error('linksrechts', location.location_code,)

        for measurement in measurements[1:-1]:
            # Tops in between should be below the banks
            if max(measurement['top'], measurement['bottom']) > first['top']:
                return self.error('tehoog', location.location_code,
                                        measurement['top'], first['top'])

        if (first['x'] == last['x']) and (first['y'] == last['y']):
            return self.error('zelfdexy', location.location_code,)

        # Points should be close to each other. We set the limit at 5m because
        # of measurement inaccuracy.
        limit = 5

        for measurement1, measurement2 in zip(measurements, measurements[1:]):
            # Helpfully, RD coordinates are in meters and the scale is easily
            # small enough to use them for distance measurements.
            x1, y1 = wgs84_to_rd(measurement1['x'], measurement1['y'])
            x2, y2 = wgs84_to_rd(measurement2['x'], measurement2['y'])
            distance = sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

            if distance > limit:
                return self.error("toofar", location.location_code, distance)

        return None
