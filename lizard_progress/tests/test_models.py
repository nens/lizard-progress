# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

"""Tests for lizard_progress models."""

# Python 3 is coming
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division


import datetime
import factory

from django.contrib.auth.models import User
from django.test import TestCase

from lizard_progress import models


class UserF(factory.Factory):
    FACTORY_FOR = User

    username = "admin"
    is_superuser = True


class ErrorMessageF(factory.Factory):
    FACTORY_FOR = models.ErrorMessage

    error_code = "TEST"
    error_message = "This is a test"


class OrganizationF(factory.Factory):
    """Factory for Organization model."""
    FACTORY_FOR = models.Organization

    name = "Test organization"
    is_project_owner = True


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

    organization = factory.SubFactory(OrganizationF)
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


class ExportRunF(factory.Factory):
    FACTORY_FOR = models.ExportRun

    project = factory.LazyAttribute(lambda a: ProjectF())
    contractor = factory.LazyAttribute(lambda a: ContractorF())
    measurement_type = factory.LazyAttribute(
        lambda a: AvailableMeasurementTypeF())
    exporttype = "someexporttype"
    generates_file = True
    created_at = None
    created_by = None
    file_path = None
    ready_for_download = False
    export_running = False


class TestUser(TestCase):
    """Tests for the User model."""
    def test_username(self):
        user = UserF(username="admin")
        self.assertEquals(user.username, "admin")


class TestErrorMessage(TestCase):
    def test_has_unicode(self):
        em = ErrorMessageF.build()
        self.assertTrue(unicode(em))

    def test_format_formats(self):
        em = ErrorMessageF.build(error_message="Testing {0} {other}")
        self.assertEquals(
            em.format("one", other="two"),
            "Testing one two")

    def test_format_code_using_unknown_code(self):
        code, error = models.ErrorMessage.format_code(error_code="SOME CODE")
        self.assertEquals(code, "UNKNOWNCODE")
        self.assertTrue("SOME CODE" in error)

    def test_format_code_works(self):
        ErrorMessageF.create(
            error_code="TEST",
            error_message="Some {format} string")

        code, error = models.ErrorMessage.format_code(
            error_code="TEST", format="format")

        self.assertEquals(code, "TEST")
        self.assertEquals(error, "Some format string")


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

    def test_has_role_false(self):
        userprofile = UserProfileF(
            user=UserF(username="admin"),
            organization=OrganizationF(name="test"))
        self.assertFalse(userprofile.has_role(models.UserRole.ROLE_ADMIN))

    def test_has_role_true(self):
        userprofile = UserProfileF(
            user=UserF(username="admin"),
            organization=OrganizationF(name="test"))
        userprofile.roles.add(
            models.UserRole.objects.get(code=models.UserRole.ROLE_ADMIN))
        self.assertTrue(userprofile.has_role(models.UserRole.ROLE_ADMIN))


class TestSecurity(TestCase):
    """Test for security."""
    def test_has_access_contractor(self):
        """Test access for contractor to a project."""
        uploader = UserF.create(username="uploader", is_superuser=False)
        uploaderorganization = OrganizationF.create(name="Uploader organization")
        UserProfileF.create(
            user=uploader, organization=uploaderorganization)
        projectorganization = OrganizationF.create(name="organization")
        projectuser = UserF(is_superuser=True)
        project = ProjectF.create(superuser=projectuser)
        UserProfileF.create(
            user=projectuser, organization=projectorganization)
        contractor = ContractorF(
            project=project, organization=uploaderorganization)
        has_access = models.has_access(uploader, project, contractor)
        self.assertEquals(has_access, True)


class TestProject(TestCase):
    def test_set_slug_and_save(self):
        organization = OrganizationF.create()

        project = ProjectF.build(
            name="Test Project",
            organization=organization)

        project.set_slug_and_save()
        self.assertTrue(project.slug)
        self.assertTrue(unicode(project.id) in project.slug)
        self.assertTrue("test-project" in project.slug)


class TestContractor(TestCase):
    """Tests for the Contractor model."""
    def test_unicode(self):
        """Tests unicode method."""
        contractor = ContractorF(
            name="test", project=ProjectF(name="testproject"))
        self.assertEquals(unicode(contractor), "test in testproject")

    def test_set_slug_and_save(self):
        organization = OrganizationF.create(name="some_org")
        user = UserF.create(username="whee")
        UserProfileF.create(
            user=user,
            organization=organization)
        project = ProjectF.create(name="testproject", superuser=user)

        contractor = ContractorF.build(
            project=project,
            name="test",
            organization=organization,
            slug=None)

        contractor.set_slug_and_save()
        self.assertTrue(contractor.slug)
        self.assertTrue(unicode(contractor.id) in contractor.slug)
        self.assertTrue("some_org" in contractor.slug)

    def test_show_measurement_type(self):
        """Just checking that it doesn't crash"""
        contractor = ContractorF.create()
        measurement_type = MeasurementTypeF.create(
            project=contractor.project)
        contractor.show_measurement_type(measurement_type)


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
        MeasurementF(scheduled=scheduled)
        MeasurementF(scheduled=scheduled)
        self.assertRaises(Exception, lambda: scheduled.measurement)


class TestMeasurement(TestCase):
    """Tests for the Measurement model."""
    def test_url_works(self):
        """Just check whether we get some URL."""
        measurement = MeasurementF()
        url = measurement.url
        self.assertTrue(url)


class TestExportRun(TestCase):
    def test_exportrun_without_file_is_not_available(self):
        project = ProjectF.create()
        contractor = ContractorF.create(project=project)
        run = ExportRunF.build(
            project=project,
            contractor=contractor,
            file_path="/some/nonexisting/path",
            generates_file=True)
        self.assertFalse(run.available)

    def test_exportrun_has_run_doesnt_generate_file_is_available(self):
        project = ProjectF.create()
        contractor = ContractorF.create(project=project)
        run = ExportRunF.build(
            project=project,
            contractor=contractor,
            generates_file=False,
            created_at=datetime.datetime(1980, 1, 1))
        self.assertTrue(run.available)
