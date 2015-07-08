import datetime

import osgeo.ogr

from lizard_progress.tests import test_models

from lizard_progress.parsers import ribx_parser

from lizard_progress.tests.base import FixturesTestCase

# Some helper variables for when the actual value doesn't matter.
today = datetime.date.today()
amersfoort = osgeo.ogr.Geometry(osgeo.ogr.wkbPoint)
amersfoort.AddPoint(155000, 463000)


class MockItem(object):
    """Used instead of a drain, manhole, or pipe."""
    def __init__(
            self, ref, inspection_date, geom, sourceline=None, media=None):
        self.ref = ref
        self.inspection_date = inspection_date
        self.geom = geom
        self.sourceline = sourceline
        self.new = False
        self.work_impossible = None
        if media is not None:
            self.media = media
        else:
            self.media = set()


class TestSaveMeasurement(FixturesTestCase):
    def setUp(self):
        self.mtype = test_models.AvailableMeasurementTypeF.create(
            slug='ribx_reiniging_inspectie_riool')
        self.activity = test_models.ActivityF.create(
            measurement_type=self.mtype)
        self.parser = ribx_parser.RibxParser(self.activity, None)
        self.location = test_models.LocationF.create(
            activity=self.activity, location_code='testref')

    def test_unknown_location_returns_none(self):
        item = MockItem('wrongref', today, amersfoort)
        self.assertEquals(self.parser.save_measurement(item), None)

    def test_create_measurement_without_files(self):
        item = MockItem('testref', today, amersfoort, [])

        measurement = self.parser.save_measurement(item)
        self.assertTrue(measurement.location.complete)
        self.assertEquals(self.location, measurement.location)

    def test_find_existing_ribx_measurement_two_measurements(self):
        """Save two measurements, only one of which has the right filetype."""
        test_models.MeasurementF.create(
            location=self.location, date=today,
            data={'filetype': 'media'})
        m2 = test_models.MeasurementF.create(
            location=self.location, date=today,
            data={'filetype': 'ribx'})

        m3 = self.parser.find_existing_ribx_measurement(
            self.location, today)

        self.assertEquals(m3.id, m2.id)

    def test_find_existing_ribx_measurement_one_wrong_measurement(self):
        """Save one measurement, with the wrong filetype."""
        test_models.MeasurementF.create(
            location=self.location, date=today,
            data={'filetype': 'media'})

        m = self.parser.find_existing_ribx_measurement(
            self.location, today)

        self.assertEquals(m, None)
