# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.txt.
"""Tests that don't belong elsewhere"""

from django.conf import settings
from django.test import TestCase

from lizard_progress import views
from lizard_progress.layers import ProgressAdapter
from lizard_progress.models import Project, Contractor,\
    MeasurementType, AvailableMeasurementType
from lizard_map.models import WorkspaceEdit, WorkspaceEditItem
from lizard_progress.specifics import ProgressParser, UnSuccessfulParserResult


class AdapterTest(TestCase):
    def setUp(self):
        self.workspace = WorkspaceEdit()
        self.workspace.save()
        self.workspace_item = WorkspaceEditItem(workspace=self.workspace)
        self.workspace_item.save()

    def init_adapter(self, layer_arguments, project,
                     contractor, measurement_type):
        # Create adapter with given layer_arguments
        self.adapter = ProgressAdapter(workspace_item=self.workspace_item,
                                       layer_arguments=layer_arguments)

        # Check if project, contractor and measurement_type are as expected
        self.assertEquals(self.adapter.project, project)
        self.assertEquals(self.adapter.contractor, contractor)
        self.assertEquals(self.adapter.measurement_type, measurement_type)

    def test_empty_adapter(self):
        self.init_adapter({}, None, None, None)

    def test_unexisting_adapter(self):
        self.init_adapter({'project_slug': 'wheeeeeee'}, None, None, None)

    def test_weird_adapter_input(self):
        self.assertRaises(
            ValueError, self.init_adapter, None, None, None, None)

    def test_full_adapter(self):
        project = Project(slug='test')
        project.save()
        contractor = Contractor(slug='contractor')
        contractor.project = project
        contractor.save()
        available_measurement_type = AvailableMeasurementType(slug='mtype')
        available_measurement_type.save()
        measurement_type = MeasurementType(mtype=available_measurement_type)
        measurement_type.project = project
        measurement_type.save()

        self.init_adapter({
                'project_slug': 'test',
                'contractor_slug': 'contractor',
                'measurement_type_slug': 'mtype',
                }, project, contractor, measurement_type)


class TestParsers(TestCase):
    class MockParser(ProgressParser):
        ERRORS = {'key': 'value %s'}

    class MockLa(object):
        line_number = 1

    class MockFileObject:
        name = 'filename'

    def setUp(self):
        self.parser = TestParsers.MockParser(None, None, None)

    def test_error(self):
        result = self.parser.error('key')  # No message, but shouldn't fail
        self.assertTrue(isinstance(result, UnSuccessfulParserResult))

        self.assertEqual(result.error, 'Fout: value %s')

        result = self.parser.error('key', 'arg')
        self.assertEqual(result.error, 'Fout: value arg')

        # If there is a file object with a name, add it to the error message
        self.parser.file_object = TestParsers.MockFileObject()
        result = self.parser.error('key', 'arg')
        self.assertEqual(result.error, 'filename: Fout: value arg')

        # With a la object we get a line number
        self.parser.la = TestParsers.MockLa()
        result = self.parser.error('key')
        self.assertEqual(result.error, 'filename: Fout op regel 0: value %s')
