"""Tests for lizard_progress models."""

import factory

from django.test import TestCase

from lizard_progress import models
from lizard_progress.specifics import Specifics


class ProjectF(factory.Factory):
    """Factory for Project models."""

    FACTORY_FOR = models.Project

    name = "Test project"
    slug = "testproject"


class ContractorF(factory.Factory):
    """Factory for Contractor models."""
    FACTORY_FOR = models.Contractor

    project = factory.LazyAttribute(lambda a: ProjectF())
    name = "Nelen & Schuurmans"
    slug = "nens"
    user = None


class AreaF(factory.Factory):
    """Factory for Area models."""
    FACTORY_FOR = models.Area

    project = factory.LazyAttribute(lambda a: ProjectF())
    name = "Zuidpool"
    slug = "zuidpool"


class LocationF(factory.Factory):
    """Factory for Location models."""
    FACTORY_FOR = models.Location

    location_code = "SOME_ID"
    project = factory.LazyAttribute(lambda a: ProjectF())
    area = factory.LazyAttribute(lambda a: AreaF(project=a.project))

    information = {"key": "value"}


class AvailableMeasurementTypeF(factory.Factory):
    FACTORY_FOR = models.AvailableMeasurementType

    name = "Metingtype"
    slug = "metingtype"


class MeasurementTypeF(factory.Factory):
    """Factory for MeasurementType objects."""
    FACTORY_FOR = models.MeasurementType

    mtype = factory.LazyAttribute(lambda a: AvailableMeasurementTypeF())
    project = factory.LazyAttribute(lambda a: ProjectF())


class ScheduledMeasurementF(factory.Factory):
    """Factory for ScheduledMeasurement objects."""
    FACTORY_FOR = models.ScheduledMeasurement

    project = factory.LazyAttribute(lambda a: ProjectF())
    contractor = factory.LazyAttribute(
        lambda a: ContractorF(project=a.project))
    measurement_type = factory.LazyAttribute(
        lambda a: MeasurementTypeF(project=a.project))
    location = factory.LazyAttribute(lambda a: LocationF(project=a.project))
    complete = False


class MeasurementF(factory.Factory):
    """Factory for Measurement objects."""
    FACTORY_FOR = models.Measurement

    scheduled = factory.LazyAttribute(lambda a: ScheduledMeasurementF())
    data = {"testkey": "testvalue"}
    filename = "test.txt"


class TestProject(TestCase):
    """Tests for the Project model."""

    def test_specifics_unknown(self):
        """Getting specifics for an unknown project should return None."""

        project = ProjectF.build()

        self.assertEquals(project.specifics(), None)

    def test_specifics_importerror(self):
        """Getting specifics for a project with an entry point that
        can't be imported should raise an exception."""

        project = ProjectF.build()

        class MockEntryPoint(object):
            """No functionality except for failed loading."""
            name = project.slug

            def load(self):
                """I can't be loaded."""
                raise ImportError("mock")

        self.assertRaises(
            ImportError,
            lambda: Specifics(project, entrypoints=[MockEntryPoint()]))


class TestContractor(TestCase):
    """Tests for the Contractor model."""
    def test_unicode(self):
        """Tests unicode method."""
        contractor = ContractorF(
            name="test", project=ProjectF(name="testproject"))
        self.assertEquals(unicode(contractor), "test in testproject")


class TestArea(TestCase):
    """Tests for the Area model."""
    def test_unicode(self):
        """Tests unicode method."""
        area = AreaF(name="test", project=ProjectF(name="testproject"))
        self.assertEquals(unicode(area), "test in testproject")


class TestLocation(TestCase):
    """Tests for the Location model."""
    def test_unicode(self):
        """Tests unicode method."""
        location = LocationF(location_code="TESTID", area=None)
        self.assertEquals(unicode(location), "Location with code 'TESTID'")


class TestMeasurementType(TestCase):
    """Tests for the MeasurementType model."""
    def test_unicode(self):
        """Tests unicode method."""
        mtype = MeasurementTypeF(
            name='testtype', project=ProjectF(name='testproject'))
        self.assertEquals(unicode(mtype), "Type 'Metingtype' in testproject")


class TestScheduledMeasurement(TestCase):
    """Tests for the ScheduledMeasurement model."""
    def test_unicode(self):
        """Tests unicode method."""
        project = ProjectF(name='testproject')
        scheduled = ScheduledMeasurementF(
            project=project,
            measurement_type=MeasurementTypeF(
                project=project, name='testtype'),
            location=LocationF(project=project, location_code='TEST'),
            contractor=ContractorF(project=project, name="testcontractor"))

        self.assertEquals(
            unicode(scheduled),
            ("Scheduled measurement of type 'Metingtype' at location 'TEST' "
             "in project 'testproject' by contractor 'testcontractor'."))

    def test_measurement(self):
        """Tests the measurement property."""
        scheduled = ScheduledMeasurementF()
        measurement = MeasurementF(scheduled=scheduled)

        self.assertEqual(scheduled.measurement, measurement)

    def test_measurement_exception(self):
        """Two measurements for one scheduled should mean that the measurement
        property fails."""
        scheduled = ScheduledMeasurementF()
        m1 = MeasurementF(scheduled=scheduled)
        m2 = MeasurementF(scheduled=scheduled)
        self.assertRaises(Exception, lambda: scheduled.measurement)
        m1, m2  # pyflakes


class TestMeasurement(TestCase):
    """Tests for the Measurement model."""
    def test_url_works(self):
        """Just check whether we get some URL."""
        measurement = MeasurementF()
        url = measurement.url
        self.assertTrue(url)
