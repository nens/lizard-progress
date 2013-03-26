"""Machinery to give actual .MET files to the MET parser, to see if it
returns the expected errors."""


from django.test import TestCase

import importlib
import mock

from pkg_resources import resource_filename

from lizard_progress import models
from lizard_progress import process_uploaded_file
from lizard_progress.tests import test_models

migration_0007 = importlib.import_module(
    'lizard_progress.migrations.0007_add_error_messages')
migration_0011 = importlib.import_module(
    'lizard_progress.migrations.0011_add_more_error_codes')


def create_org_and_user(
    orgname, username, is_project_owner,
    allows_non_predefined_locations=False):
    organization = test_models.OrganizationF.create(
        name=orgname,
        is_project_owner=is_project_owner,
        allows_non_predefined_locations=allows_non_predefined_locations)
    user = test_models.UserF.create(username=username, is_superuser=False)
    test_models.UserProfileF.create(user=user, organization=organization)

    return organization, user


def dwarsprofiel_available_mtype():
    amt, created = models.AvailableMeasurementType.objects.get_or_create(
        name="Dwarsprofiel",
        slug="dwarsprofiel",
        needs_predefined_locations=False,
        likes_predefined_locations=True,
        needs_scheduled_measurements=False)
    return amt


@mock.patch('shutil.move')  # So that the file isn't moved for real in the end
class TestWaternet(TestCase):
    def setUp(self):
        # Insanely, this is necessary. See
        # http://stackoverflow.com/questions/6584671/django-1-3-and-south-migrations
        migration_0007.add_more_error_codes(models.ErrorMessage)
        migration_0011.add_more_error_codes(models.ErrorMessage)

        self.project_org, self.project_user = create_org_and_user(
            'Waternet', 'waternet', True,
            allows_non_predefined_locations=True)

        self.upload_org, self.upload_user = create_org_and_user(
            'Testuploader', 'test', False)

        self.project = test_models.ProjectF.create(
            name="testproject",
            slug="testproject",
            superuser=self.project_user)

        self.contractor = test_models.ContractorF.create(
            project=self.project,
            organization=self.upload_org)

        self.measurementtype = test_models.MeasurementTypeF.create(
            project=self.project,
            mtype=dwarsprofiel_available_mtype())

    def setup_uploaded_file(self, path):
        uploaded_file = test_models.UploadedFileF.create(
            project=self.project,
            contractor=self.contractor,
            uploaded_by=self.upload_user,
            path=path)
        return uploaded_file

    def get_errors(self, uploaded_file):
        return list(uploaded_file.uploadedfileerror_set.all())

    def try_file(self, filename, expected_errors=None):
        """Expected_errors is an iterable of (line, error_code) pairs."""

        path = resource_filename(
            'lizard_progress',
            'tests/test_met_files/' + filename)
        uploaded_file = self.setup_uploaded_file(path)
        process_uploaded_file.process_uploaded_file(uploaded_file.id)
        errors = self.get_errors(uploaded_file)

        # Process_uploaded_file gets a fresh instance from the database, so
        # our old one isn't updated
        uploaded_file = models.UploadedFile.objects.get(
            pk=uploaded_file.id)

        # Helpful in case this fails
        print(path)
        print(expected_errors)
        print(errors)

        if not expected_errors:
            self.assertTrue(uploaded_file.success)
            self.assertEquals(len(errors), 0)
        else:
            self.assertFalse(uploaded_file.success)
            self.assertEquals(len(errors), len(expected_errors))
            for error in errors:
                self.assertTrue((error.line, error.error_code)
                                in expected_errors)

    def test_correct_file(self, *args):
        self.try_file(
            'waternet/a/Metfile_Goed.met',
            set())

    def test_versienummer_correct(self, *args):
        self.try_file(
            'waternet/a/1 Versienummer_correct.met',
            set([(1, 'MET_WRONGVERSION')]))

    def test_versienummer_aanwezig(self, *args):
        self.try_file(
            'waternet/a/1 Versienummer_aanwezig.met',
            set([(1, 'MET_NOVERSION')]))
