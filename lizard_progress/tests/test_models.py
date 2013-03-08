"""Tests for lizard_progress models."""

import datetime
import factory

from django.contrib.auth.models import User
from django.test import TestCase

from lizard_progress import models


class UserF(factory.Factory):
    FACTORY_FOR = User

    username = "admin"
    is_superuser = True


class OrganizationF(factory.Factory):
    """Factory for Organization model."""
    FACTORY_FOR = models.Organization

    name = "Test organization"


class UserProfileF(factory.Factory):
    """Factory for UserProfile model."""

    FACTORY_FOR = models.UserProfile

    user = factory.SubFactory(UserF)
    organization = factory.LazyAttribute(lambda a: OrganizationF())


class ProjectF(factory.Factory):
    """Factory for Project models."""

    FACTORY_FOR = models.Project

    name = "Test project"
    slug = "testproject"
    superuser = factory.SubFactory(UserF)


class ContractorF(factory.Factory):
    """Factory for Contractor models."""
    FACTORY_FOR = models.Contractor

    project = factory.LazyAttribute(lambda a: ProjectF())
    name = "Nelen & Schuurmans"
    slug = "nens"
    organization = None


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


class UploadedFileF(factory.Factory):
    """Factory for UploadedFile models."""
    FACTORY_FOR = models.UploadedFile

    project = factory.LazyAttribute(lambda a: ProjectF())
    contractor = factory.LazyAttribute(lambda a: ContractorF())
    uploaded_by = factory.LazyAttribute(lambda a: UserF())
    uploaded_at = datetime.datetime(2013, 3, 8, 10, 0)
    path = "/path/to/file/file.met"
    ready = False
    linelike = True


class UploadedFileErrorF(factory.Factory):
    FACTORY_FOR = models.UploadedFileError

    uploaded_file = factory.LazyAttribute(lambda a: UploadedFileF())
    line = 0
    error_code = "NOCODE"
    error_message = "Some error message"


class TestUser(TestCase):
    """Tests for the User model."""
    def test_username(self):
        user = UserF(username="admin")
        self.assertEquals(user.username, "admin")


class TestOrganization(TestCase):
    """Tests for the Organization model."""
    def setUp(self):
        self.organization = OrganizationF(name="test")

    def test_unicode(self):
        """Test unicode method."""
        self.assertEquals(unicode(self.organization), "test")

    def test_users_in_same_organization(self):
        """Test users_in_same_organization method."""
        user1 = UserF(username="user1")
        user2 = UserF(username="user2")
        UserProfileF(user=user1,
                     organization=self.organization)
        UserProfileF(user=user2,
                     organization=self.organization)
        users = self.organization.users_in_same_organization(user1)
        self.assertEquals(len(users), 2)


class TestUserProfile(TestCase):
    """Tests for the UserProfile model."""
    def test_unicode(self):
        """Test unicode method."""
        userprofile = UserProfileF(
            user=UserF(username="admin"),
            organization=OrganizationF(name="test"))
        self.assertEquals(unicode(userprofile), "admin test")


class TestSecurity(TestCase):
    """Test for security."""
    def test_has_access_superuser(self):
        """Test access for superuser to a project."""
        user = UserF(is_superuser=True)
        project = ProjectF(superuser=user)
        has_access = models.has_access(user, project)
        self.assertEquals(has_access, True)

    def test_has_access_contractor(self):
        """Test access for contractor to a project."""
        uploader = UserF(username="uploader", is_superuser=False)
        uploaderorganization = OrganizationF(name="Uploader organization")
        UserProfileF(
            user=uploader, organization=uploaderorganization)
        project = ProjectF(superuser=UserF(is_superuser=True))
        contractor = ContractorF(
            project=project, organization=uploaderorganization)
        has_access = models.has_access(uploader, project, contractor)
        self.assertEquals(has_access, True)


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
