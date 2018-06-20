# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

"""Tests for lizard_progress util.AutoReviewer"""


from lizard_progress.tests.base import FixturesTestCase
from lizard_progress.util import AutoReviewer
from lizard_progress.util import Observation
from lizard_progress.util import Field

import os


class TestAutoReviewer(FixturesTestCase):

    def setUp(self):
        self.filterfile = os.path.join('lizard_progress',
                                       'util',
                                       'tests',
                                       'test_autoreviewer_files',
                                       'filter_complete_valid.xlsx')

        self.ar = AutoReviewer(self.filterfile)

    def test_count_rules(self):
        res = self.ar.count_rules()
        self.assertEquals(res, 20)

    def test_observations(self):
        # Let's start with single observations
        test_cases = {Observation([Field('A', 'BAA'), Field('B', 'Z'), Field('D', '10')]): 'INTERVENE',
                      Observation([Field('A', 'BAA'), Field('B', 'Z'), Field('D', '6')]): 'WARN',
                      Observation([Field('A', 'BAF'), Field('B', 'Z'), Field('C', 'Z')]): 'WARN',
                      Observation([Field('A', 'BZF'), Field('B', 'Z'), Field('C', 'Z')]): 'NORULE',
        }

        for obs, expected in test_cases:
            self.assertEquals(self.ar.filterTable.test_observation(obs), expected)
