import datetime

import osgeo.ogr

from django.test import TestCase

from lizard_progress import models
from lizard_progress.tests import test_models

from lizard_progress.parsers import ribx_parser

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
        if media is not None:
            self.media = media


class TestSaveMeasurement(TestCase):
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
