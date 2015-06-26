from __future__ import unicode_literals, division
from __future__ import print_function, absolute_import

from cStringIO import StringIO

from mock import MagicMock

from lizard_progress.util import metfile
from lizard_progress.tests.base import FixturesTestCase


class TestTrivialReeks(FixturesTestCase):
    def test_trivial(self):
        mockfile = StringIO()
        measurement = MagicMock()
        measurement.scheduled.location.location_code = "testcode"

        metfile.write_trivial_reeks(mockfile, measurement)

        self.assertEquals(
            mockfile.getvalue(),
            "<REEKS>testcode,testcode,</REEKS>\n")

    def test_removes_dwarsprofiel_code(self):
        mockfile = StringIO()
        measurement = MagicMock()
        measurement.scheduled.location.location_code = "testcode-123"

        metfile.write_trivial_reeks(mockfile, measurement)

        self.assertEquals(
            mockfile.getvalue(),
            "<REEKS>testcode,testcode,</REEKS>\n")
