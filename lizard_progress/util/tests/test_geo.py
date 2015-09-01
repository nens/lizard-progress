from django.test import TestCase

from osgeo import ogr

from lizard_progress.util import geo


class TestIsLine(TestCase):
    def test_with_point(self):
        amersfoort = ogr.Geometry(ogr.wkbPoint)
        amersfoort.AddPoint(155000, 463000)

        self.assertFalse(geo.is_line(amersfoort))


class TestGetMidpoint(TestCase):
    def test_with_simple_line(self):
        line = ogr.CreateGeometryFromWkt(
            'LINESTRING(0 0, 2 2)')

        point = geo.get_midpoint(line)
        self.assertEquals(point.GetX(), 1)
        self.assertEquals(point.GetY(), 1)
