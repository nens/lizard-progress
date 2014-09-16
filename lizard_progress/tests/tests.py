# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.txt.
"""Tests that don't belong elsewhere"""

from django.test import TestCase

from lizard_progress.models import Activity
from lizard_progress.layers import ProgressAdapter
from lizard_progress.models import Project
from lizard_progress.models import AvailableMeasurementType
from lizard_progress.models import Organization
from lizard_map.models import WorkspaceEdit, WorkspaceEditItem
from lizard_progress.specifics import ProgressParser, UnSuccessfulParserResult

from lizard_progress.tests.test_models import ActivityF


class AdapterTest(TestCase):
    def setUp(self):
        self.workspace = WorkspaceEdit()
        self.workspace.save()
        self.workspace_item = WorkspaceEditItem(workspace=self.workspace)
        self.workspace_item.save()

    def init_adapter(self, layer_arguments, activity):
        # Create adapter with given layer_arguments
        self.adapter = ProgressAdapter(workspace_item=self.workspace_item,
                                       layer_arguments=layer_arguments)

        # Check if project, contractor and measurement_type are as expected
        self.assertEquals(self.adapter.activity, activity)

    def test_empty_adapter(self):
        self.init_adapter({}, None)

    def test_unexisting_adapter(self):
        self.init_adapter({'activity_id': 5332}, None)

    def test_weird_adapter_input(self):
        self.assertRaises(
            ValueError, self.init_adapter, None, None)

    def test_full_adapter(self):
        project = Project(
            slug='test', organization=Organization.objects.create(name="test"))
        project.save()

        available_measurement_type = AvailableMeasurementType(slug='mtype')
        available_measurement_type.save()

        activity = Activity.objects.create(
            project=project, measurement_type=available_measurement_type)

        self.init_adapter({
            'activity_id': activity.id
        }, activity)


class TestParsers(TestCase):
    class MockParser(ProgressParser):
        ERRORS = {'key': 'value %s'}

    class MockLa(object):
        line_number = 1

    class MockFileObject:
        name = 'filename'

    def setUp(self):
        self.parser = TestParsers.MockParser(ActivityF.build(), None)

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
