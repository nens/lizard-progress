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


class UserF(factory.DjangoModelFactory):
    class Meta:
        model = User

    username = "admin"
    is_superuser = True


class ErrorMessageF(factory.DjangoModelFactory):
    class Meta:
        model = models.ErrorMessage

    error_code = "TEST"
    error_message = "This is a test"


class OrganizationF(factory.DjangoModelFactory):
    """Factory for Organization model."""
    class Meta:
        model = models.Organization

    name = "Test organization"
    is_project_owner = True


class UserProfileF(factory.DjangoModelFactory):
    """Factory for UserProfile model."""

    class Meta:
        model = models.UserProfile

    user = factory.SubFactory(UserF)
    organization = factory.SubFactory(OrganizationF)


class ProjectF(factory.DjangoModelFactory):
    """Factory for Project models."""

    class Meta:
        model = models.Project

    name = "Test project"
    slug = "testproject"

    organization = factory.SubFactory(OrganizationF)


class ActivityF(factory.DjangoModelFactory):
    class Meta:
        model = models.Activity

    name = "Testactivity"
    project = factory.SubFactory(ProjectF)


class LocationF(factory.DjangoModelFactory):
    """Factory for Location models."""
    class Meta:
        model = models.Location

    location_code = "SOME_ID"
    activity = factory.SubFactory(ActivityF)

    information = {"key": "value"}


class AvailableMeasurementTypeF(factory.DjangoModelFactory):
    class Meta:
        model = models.AvailableMeasurementType

    name = "Metingtype"
    slug = "metingtype"


class ScheduledMeasurementF(factory.DjangoModelFactory):
    """Factory for ScheduledMeasurement objects."""
    class Meta:
        model = models.ScheduledMeasurement

    activity = factory.SubFactory(ActivityF)
    organization = factory.SubFactory(OrganizationF)
    available_measurement_type = factory.SubFactory(
        AvailableMeasurementTypeF)
    location = factory.SubFactory(LocationF)
    complete = False


class MeasurementF(factory.DjangoModelFactory):
    """Factory for Measurement objects."""
    class Meta:
        model = models.Measurement

    scheduled = factory.SubFactory(ScheduledMeasurementF)
    data = {"testkey": "testvalue"}
    filename = "test.txt"


class UploadedFileF(factory.DjangoModelFactory):
    """Factory for UploadedFile models."""
    class Meta:
        model = models.UploadedFile

    activity = factory.SubFactory(ActivityF)
    organization = factory.SubFactory(OrganizationF)
    uploaded_by = factory.SubFactory(UserF)
    uploaded_at = datetime.datetime(2013, 3, 8, 10, 0)
    path = "/path/to/file/file.met"
    ready = False
    linelike = True


class UploadedFileErrorF(factory.DjangoModelFactory):
    class Meta:
        model = models.UploadedFileError

    uploaded_file = factory.SubFactory(UploadedFileF)
    line = 0
    error_code = "NOCODE"
    error_message = "Some error message"


class ExportRunF(factory.DjangoModelFactory):
    class Meta:
        model = models.ExportRun

    project = factory.SubFactory(ProjectF)
    organization = factory.SubFactory(OrganizationF)
    measurement_type = factory.SubFactory(AvailableMeasurementTypeF)

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

    def test_allowed_measurement_types_is_none_at_first(self):
        organization = OrganizationF.create(name="mtypetest")
        self.assertEquals(
            len(organization.allowed_available_measurement_types()), 0)

    def test_allowed_measurement_type_not_allowed(self):
        organization = OrganizationF.create(name="mtypetest")
        AvailableMeasurementTypeF.create()
        self.assertEquals(
            len(organization.allowed_available_measurement_types()), 0)

    def test_allowed_measurement_types_allowed_if_added(self):
        organization = OrganizationF.create(name="mtypetest")
        amt = AvailableMeasurementTypeF.create()
        models.MeasurementTypeAllowed.objects.create(
            organization=organization, mtype=amt)
        self.assertEquals(
            len(organization.allowed_available_measurement_types()), 1)

    def test_allowed_invisible_mtype_is_not_visible(self):
        organization = OrganizationF.create(name="mtypetest")
        amt = AvailableMeasurementTypeF.create()
        models.MeasurementTypeAllowed.objects.create(
            organization=organization, mtype=amt, visible=False)
        self.assertEquals(
            len(organization.visible_available_measurement_types()), 0)

    def test_allowed_visible_mtype_is_visible(self):
        organization = OrganizationF.create(name="mtypetest")
        amt = AvailableMeasurementTypeF.create()
        models.MeasurementTypeAllowed.objects.create(
            organization=organization, mtype=amt, visible=True)
        self.assertEquals(
            len(organization.visible_available_measurement_types()), 1)


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
        uploaderorganization = OrganizationF.create(
            name="Uploader organization")
        profile = UserProfileF.create(
            user=uploader, organization=uploaderorganization)
        profile.roles.add(
            models.UserRole.objects.get(
                code=models.UserRole.ROLE_UPLOADER))

        projectorganization = OrganizationF.create(name="organization")
        projectuser = UserF(is_superuser=True)
        project = ProjectF.create()
        UserProfileF.create(
            user=projectuser, organization=projectorganization)
        contractor = ContractorF(
            project=project, organization=uploaderorganization)
        has_access = models.has_access(uploader, project, contractor)
        self.assertTrue(has_access)


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

    def test_num_open_change_requests_returns_one(self):
        from lizard_progress.changerequests.tests.test_models import RequestF
        organization = OrganizationF.create(name='A')
        project = ProjectF.create(organization=organization)
        organizationB = OrganizationF.create(name='B')
        contractor = ContractorF.create(
            project=project, organization=organizationB)

        RequestF.create(contractor=contractor)
        self.assertEquals(project.num_open_requests, 1)

    def test_num_open_change_requests_returns_zero(self):
        organization = OrganizationF.create(name='A')
        project = ProjectF.create(organization=organization)

        self.assertEquals(project.num_open_requests, 0)


class TestLocation(TestCase):
    """Tests for the Location model."""
    def test_unicode(self):
        """Tests unicode method."""
        location = LocationF(location_code="TESTID")
        self.assertEquals(unicode(location), "Location with code 'TESTID'")


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

    def test_exportrun_that_fails_is_not_available(self):
        project = ProjectF.create()
        contractor = ContractorF.create(project=project)
        run = ExportRunF.build(
            project=project,
            contractor=contractor,
            file_path=None,
            generates_file=True)

        run.record_start(None)
        run.fail("Testmessage")

        # Retrieve from database
        run = models.ExportRun.objects.get(pk=run.id)

        self.assertEquals(run.error_message, "Testmessage")
        self.assertFalse(run.export_running)
        self.assertFalse(run.available)
