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

from django.contrib.gis.geos import Point
from django.contrib.auth.models import User
from django.test import TestCase
from django.test import TransactionTestCase

from lizard_progress import models


class UserF(factory.DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ('username',)

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


class MeasurementF(factory.DjangoModelFactory):
    """Factory for Measurement objects."""
    class Meta:
        model = models.Measurement

    location = factory.SubFactory(LocationF)
    data = {"testkey": "testvalue"}
    filename = "test.txt"


class UploadedFileF(factory.DjangoModelFactory):
    """Factory for UploadedFile models."""
    class Meta:
        model = models.UploadedFile

    activity = factory.SubFactory(ActivityF)
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

    activity = factory.SubFactory(ActivityF)

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


class TestOrganization(TransactionTestCase):
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

    fixtures = ['userroles.json']

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

    fixtures = ['userroles.json']

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
        project = ProjectF.create(organization=projectorganization)
        UserProfileF.create(
            user=projectuser, organization=projectorganization)

        ActivityF.create(
            project=project, contractor=uploaderorganization)

        has_access = models.has_access(uploader, project, uploaderorganization)
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
        activity = ActivityF.create(
            project=project, contractor=organizationB)

        RequestF.create(activity=activity)
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

    def test_measurement(self):
        """Tests the measurement property."""
        location = LocationF()
        measurement = MeasurementF(location=location)

        self.assertEqual(location.measurement, measurement)

    def test_measurement_exception(self):
        """Two measurements for one scheduled should mean that the measurement
        property fails."""
        location = LocationF()
        MeasurementF(location=location)
        MeasurementF(location=location)
        self.assertRaises(Exception, lambda: location.measurement)

    def test_has_measurements(self):
        location = LocationF()
        MeasurementF(location=location)

        self.assertTrue(location.has_measurements())


class TestMeasurement(TestCase):
    """Tests for the Measurement model."""
    def test_url_works(self):
        """Just check whether we get some URL."""
        measurement_type = AvailableMeasurementTypeF.create(slug="test")
        activity = ActivityF.create(measurement_type=measurement_type)
        location = LocationF.create(activity=activity)
        measurement = MeasurementF.create(location=location)
        url = measurement.url
        self.assertTrue(url)

    def test_record_location(self):
        activity = ActivityF.create()
        location = LocationF(
            activity=activity, location_code="whee", the_geom=None)
        measurement = MeasurementF(location=location)
        point = Point(0, 0)
        measurement.record_location(point)
        self.assertEquals(location.the_geom, point)


class TestExportRun(TestCase):
    def test_exportrun_without_file_is_not_available(self):
        measurement_type = AvailableMeasurementTypeF.build()
        contractor = OrganizationF.build()
        project = ProjectF.build()

        activity = ActivityF.build(
            measurement_type=measurement_type,
            contractor=contractor,
            project=project
        )

        run = ExportRunF.build(
            activity=activity,
            file_path="/some/nonexisting/path",
            generates_file=True)
        self.assertFalse(run.available)

    def test_exportrun_has_run_doesnt_generate_file_is_available(self):
        measurement_type = AvailableMeasurementTypeF.build()
        contractor = OrganizationF.build()
        project = ProjectF.build()

        activity = ActivityF.build(
            measurement_type=measurement_type,
            contractor=contractor,
            project=project
        )

        run = ExportRunF.build(
            activity=activity,
            file_path="/some/nonexisting/path",
            generates_file=False,
            created_at=datetime.datetime.now())

        self.assertTrue(run.available)

    def test_exportrun_that_fails_is_not_available(self):
        measurement_type = AvailableMeasurementTypeF.create()
        contractor = OrganizationF.create()
        project = ProjectF.create(
            name='test_exportrun_that_fails_is_not_available')

        activity = ActivityF.create(
            measurement_type=measurement_type,
            contractor=contractor,
            project=project
        )

        run = ExportRunF.create(
            activity=activity,
            file_path="/some/nonexisting/path",
            generates_file=True)

        run.record_start(None)
        run.fail("Testmessage")

        # Retrieve from database
        run = models.ExportRun.objects.get(pk=run.id)

        self.assertEquals(run.error_message, "Testmessage")
        self.assertFalse(run.export_running)
        self.assertFalse(run.available)


class TestActivity(TestCase):
    def test_num_locations(self):
        activity = ActivityF.create()
        LocationF.create(activity=activity, location_code='a')
        LocationF.create(activity=activity, location_code='b')
        self.assertEquals(activity.num_locations(), 2)

    def test_num_complete_locations(self):
        activity = ActivityF.create()
        LocationF.create(
            activity=activity, complete=False, location_code='a')
        LocationF.create(
            activity=activity, complete=True, location_code='b')
        LocationF.create(
            activity=activity, complete=True, location_code='c')
        self.assertEquals(activity.num_complete_locations(), 2)

    def test_get_unique_activity_name_combines_contractor_mtype(self):
        project = ProjectF.create()
        mtype = AvailableMeasurementTypeF.create(name="Testtype")
        contractor = OrganizationF.create(name="Testorg")

        self.assertEquals(
            models.Activity.get_unique_activity_name(
                project, contractor, mtype, None),
            'Testorg Testtype')

    def test_get_unique_activity_name_simply_returns_activity(self):
        project = ProjectF.create()
        mtype = AvailableMeasurementTypeF.create(name="Testtype")
        contractor = OrganizationF.create(name="Testorg")

        self.assertEquals(
            models.Activity.get_unique_activity_name(
                project, contractor, mtype, 'Activity description'),
            'Activity description')

    def test_get_unique_activity_name_returns_unique_name(self):
        project = ProjectF.create()
        mtype = AvailableMeasurementTypeF.create(name="Testtype")
        contractor = OrganizationF.create(name="Testorg")

        ActivityF.create(
            project=project, measurement_type=mtype,
            contractor=contractor, name='Testorg Testtype')
        ActivityF.create(
            project=project, measurement_type=mtype,
            contractor=contractor, name='Testorg Testtype (2)')

        self.assertEquals(
            models.Activity.get_unique_activity_name(
                project, contractor, mtype, None),
            'Testorg Testtype (3)')

    def test_get_or_create_location_returns_existing_location(self):
        activity = ActivityF.create()
        location = LocationF.create(
            activity=activity, location_code='testcode')

        location2 = activity.get_or_create_location('testcode', None)

        self.assertEquals(location.id, location2.id)

    def test_get_or_create_location_returns_from_source_activity(self):
        project = ProjectF.create()
        mtype = AvailableMeasurementTypeF.create()
        contractor = OrganizationF.create()

        activity1 = ActivityF.create(
            name='activity1', project=project, measurement_type=mtype,
            contractor=contractor)
        activity2 = ActivityF.create(
            name='activity2', project=project, measurement_type=mtype,
            contractor=contractor, source_activity=activity1)

        location = LocationF.create(
            activity=activity1, location_code='testcode', complete=True)
        MeasurementF.create(location=location)

        location2 = activity2.get_or_create_location('testcode', None)

        self.assertTrue(location2)
        self.assertNotEquals(location.id, location2.id)

    def test_get_or_create_location_ignores_locations_w_no_measurements(self):
        project = ProjectF.create()
        contractor = OrganizationF.create()
        mtype = AvailableMeasurementTypeF.create(
            needs_predefined_locations=True)

        activity1 = ActivityF.create(
            name='activity1', project=project, measurement_type=mtype,
            contractor=contractor)
        activity2 = ActivityF.create(
            name='activity2', project=project, measurement_type=mtype,
            contractor=contractor, source_activity=activity1)

        LocationF.create(
            activity=activity1, location_code='testcode', complete=True)

        self.assertRaises(
            models.Activity.NoLocationException,
            lambda: activity2.get_or_create_location('testcode', None))

    def test_latest_upload_without_upload(self):
        project = ProjectF.create()
        contractor = OrganizationF.create()
        mtype = AvailableMeasurementTypeF.create(
            needs_predefined_locations=True)

        activity = ActivityF.create(
            name='activity1', project=project, measurement_type=mtype,
            contractor=contractor)

        self.assertEquals(activity.latest_upload(), None)

    def test_latest_upload_two_uploads(self):
        project = ProjectF.create()
        contractor = OrganizationF.create()
        mtype = AvailableMeasurementTypeF.create(
            needs_predefined_locations=True)

        activity = ActivityF.create(
            name='activity1', project=project, measurement_type=mtype,
            contractor=contractor)

        today = datetime.datetime.now()
        yesterday = today - datetime.timedelta(days=1)

        UploadedFileF.create(
            activity=activity, uploaded_at=yesterday)
        UploadedFileF.create(
            activity=activity, uploaded_at=today)

        self.assertEquals(
            activity.latest_upload().uploaded_at, today)
