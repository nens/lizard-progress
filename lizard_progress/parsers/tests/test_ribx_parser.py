from django.test import TestCase
from lizard_progress.changerequests.models import Request
from lizard_progress.parsers import ribx_parser
from lizard_progress.tests import test_models
from lizard_progress.tests.base import FixturesTestCase

import datetime
import mock
import osgeo.ogr

# Some helper variables for when the actual value doesn't matter.
today = datetime.date.today()
amersfoort = osgeo.ogr.Geometry(osgeo.ogr.wkbPoint)
amersfoort.AddPoint_2D(155000, 463000)


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


class MockRibx(object):
    def __init__(self):
        self.inspection_pipes = []
        self.cleaning_pipes = []
        self.inspection_manholes = []
        self.cleaning_manholes = []
        self.drains = []


class TestLogContentParser(TestCase):
    def test_parse_log_content(self):
        # content without error
        content = [{'type': 'commentaar'}]
        errors = ribx_parser.parse_log_content(content)
        self.assertEqual(errors, [])

        # content with error
        content = [{'type': 'fout', 'bericht': 'test', 'regelnummer': '7'}]
        expected = [{'line': 7, u'message': 'GWSW: test'}]
        errors = ribx_parser.parse_log_content(content)
        self.assertEqual(errors, expected)


class TestRibxParser(FixturesTestCase):
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

    def test_unknown_location_with_new_true_is_created(self):
        # Parser needs a file_object, its name is used in the notification
        file_object = mock.MagicMock()
        file_object.name = 'testfile.ribx'
        self.parser.file_object = file_object

        item = MockItem('wrongref', today, amersfoort)
        item.new = True
        self.assertTrue(self.parser.save_measurement(item))

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

    def test_that_deletion_request_is_created(self):
        ribx = MockRibx()

        drain = MockItem(self.location.location_code, today, amersfoort)
        drain.work_impossible = 'Testing'
        ribx.drains.append(drain)

        measurements = self.parser.get_measurements(ribx)
        self.assertEquals(measurements, [])

        self.assertTrue(Request.objects.filter(
            activity=self.activity, location_code=self.location.location_code,
            request_type=Request.REQUEST_TYPE_REMOVE_CODE,
            request_status=Request.REQUEST_STATUS_OPEN).exists())

    def test_that_only_one_deletion_request_is_created(self):
        ribx = MockRibx()

        drain = MockItem(self.location.location_code, today, amersfoort)
        drain.work_impossible = 'Testing'
        ribx.drains.append(drain)
        ribx.drains.append(drain)

        measurements = self.parser.get_measurements(ribx)
        self.assertEquals(measurements, [])

        self.assertEquals(Request.objects.filter(
            activity=self.activity, location_code=self.location.location_code,
            request_type=Request.REQUEST_TYPE_REMOVE_CODE,
            request_status=Request.REQUEST_STATUS_OPEN).count(), 1)


class TestRibxParser2(FixturesTestCase):
    """Test specifics from the RibxReinigingInspectieRioolParser."""

    def setUp(self):
        self.mtype = test_models.AvailableMeasurementTypeF.create(
            slug='ribx_reiniging_inspectie_riool')
        self.activity = test_models.ActivityF.create(
            measurement_type=self.mtype)
        self.parser = ribx_parser.RibxReinigingInspectieRioolParser(
            self.activity, None)
        self.location = test_models.LocationF.create(
            activity=self.activity, location_code='testref')

    def test_find_existing_measurement(self):
        """Test the find_existing_ribx_measurement method with
        'manhole_start' argument."""
        m1 = test_models.MeasurementF.create(
            location=self.location, date=today,
            data={'filetype': 'ribx', 'manhole_start': 'foo'})
        m2 = test_models.MeasurementF.create(
            location=self.location, date=today,
            data={'filetype': 'ribx', 'manhole_start': 'bar'})

        m3 = self.parser.find_existing_ribx_measurement(
            self.location, today, 'bar')
        m4 = self.parser.find_existing_ribx_measurement(
            self.location, today, 'foo')

        self.assertEquals(m3.id, m2.id)
        self.assertEquals(m4.id, m1.id)


class TestRibxParserAngleCheck(TestCase):

    def setUp(self):
        self.inspection_pipe = mock.Mock()
        self.inspection_pipe.observations = []
        self.ribx = mock.Mock()
        self.ribx.inspection_pipes = [self.inspection_pipe]
        self.parser = ribx_parser.RibxParser(None, None)

    def test_missing_start_node(self):
        """Fail on missing start node"""
        obs_end = mock.Mock(observation_type='BDC',
                            distance=20)
        self.inspection_pipe.observations.append(obs_end)
        self.parser.check_angle_measurements(self.ribx)
        self.assertEqual(len(self.parser.errors), 1)

    def test_short_length_ok(self):
        """No errors if inspection length is less than 3 meters"""
        obs_start = mock.Mock(observation_type='BCD',
                              distance=0)
        obs_end = mock.Mock(observation_type='BDC',
                            distance=1)
        self.inspection_pipe.observations.append(obs_start)
        self.inspection_pipe.observations.append(obs_end)
        self.parser.check_angle_measurements(self.ribx)
        self.assertEqual(len(self.parser.errors), 0)

    def test_not_enough_measurements_1(self):
        """Not enough measurements (0) found"""
        obs_start = mock.Mock(observation_type='BCD',
                              distance=0)
        obs_end = mock.Mock(observation_type='BDC',
                            distance=20)
        self.inspection_pipe.observations.append(obs_start)
        self.inspection_pipe.observations.append(obs_end)
        self.parser.check_angle_measurements(self.ribx)
        self.assertEqual(len(self.parser.errors), 1)

    def test_not_enough_measurements_2(self):
        """Not enough measurements found"""
        obs_start = mock.Mock(observation_type='BCD',
                              distance=0)
        obs_end = mock.Mock(observation_type='BDC',
                            distance=20)
        for i in range(20):
            # One every meter is not enough
            obs = mock.Mock(observation_type='BXA',
                            distance=i)
            self.inspection_pipe.observations.append(obs)
        self.inspection_pipe.observations.append(obs_start)
        self.inspection_pipe.observations.append(obs_end)
        self.parser.check_angle_measurements(self.ribx)
        self.assertEqual(len(self.parser.errors), 1)

    def test_enough_measurements_2(self):
        """Not enough measurements found"""
        obs_start = mock.Mock(observation_type='BCD',
                              distance=0)
        obs_end = mock.Mock(observation_type='BDC',
                            distance=20)
        for i in range(20 * 10):
            # 10 per meter is plenty.
            obs = mock.Mock(observation_type='BXA',
                            distance=i * 0.1)
            self.inspection_pipe.observations.append(obs)
        self.inspection_pipe.observations.append(obs_start)
        self.inspection_pipe.observations.append(obs_end)
        self.parser.check_angle_measurements(self.ribx)
        self.assertEqual(len(self.parser.errors), 0)
