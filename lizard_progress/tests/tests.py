# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.txt.
"""Tests that don't belong elsewhere"""

from lizard_progress.models import Activity
from lizard_progress.models import Project
from lizard_progress.models import AvailableMeasurementType
from lizard_progress.models import Organization
from lizard_progress.specifics import ProgressParser, UnSuccessfulParserResult

from lizard_progress.tests.test_models import ActivityF
from lizard_progress.tests.base import FixturesTestCase


class TestParsers(FixturesTestCase):
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
