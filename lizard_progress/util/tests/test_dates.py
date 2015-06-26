from __future__ import unicode_literals, division
from __future__ import print_function, absolute_import

import datetime

from lizard_progress.util import dates
from lizard_progress.tests.base import FixturesTestCase


class TestWeeknumberToDate(FixturesTestCase):
    def test_2015_01_21(self):
        # Today at the time of writing this
        self.assertEquals(
            dates.weeknumber_to_date(2015, 4, 3),
            datetime.date(year=2015, month=1, day=21))

    def test_jan_1_2012(self):
        # Because it is tricky
        self.assertEquals(
            dates.weeknumber_to_date(2011, 52, 7),
            datetime.date(year=2012, month=1, day=1))

    def test_jan_1_2015(self):
        # Because it is normal
        self.assertEquals(
            dates.weeknumber_to_date(2015, 1, 4),
            datetime.date(year=2015, month=1, day=1))
