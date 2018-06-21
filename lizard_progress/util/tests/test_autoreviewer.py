# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

"""Tests for lizard_progress util.AutoReviewer
Content of the filter file (converted to CSV):
HCTag,Hoofdcode,Kar 1 Tag,Kar 1 val,Kar 2 Tag,Kar 2 val,Kwant 1,Plaats omtrek,Waarschuwing,Ingrijp
<A> </A>,BAA,,,,,<D> </D>,,>5,>=10
<A> </A>,BAB,<B> </B>,,,,,,"B, C",
<A> </A>,BAC,<B> </B>,,,,,,A,"B, C"
<A> </A>,BAD,,,,,,,,
<A> </A>,BAE,,,,,,,,
<A> </A>,BAF,<B> </B>,"E, F, G, I",<C> </C>,,,,A,
<A> </A>,BAF,<B> </B>,"C, D, E, F, G, H, I",<C> </C>,,,,B,
<A> </A>,BAF,<B> </B>,"C, D, E, F, G, H, I",<C> </C>,,,,C en D,
<A> </A>,BAF,<B> </B>,alle waarnemingen,<C> </C>,,,,E en Z,
<A> </A>,BAG,,,,,<D> </D>,,>25,
<A> </A>,BAH,<B> </B>,,,,,,"E, Z",
<A> </A>,BAI,<B> </B>,A,<C> </C>,,,,"B, C, D",
<A> </A>,BAJ,<B> </B>,B,,,<D> </D>,,10,
<A> </A>,BAK,<B> </B>,,,,,,"A, B, C, E, F, G, H, I, J, K",
<A> </A>,BAL,,,,,,,,
<A> </A>,BAM,,,,,,,,
<A> </A>,BAN,,,,,,,,
<A> </A>,BAO,,,,,<G> </G>,,,0
<A> </A>,BAP,,,,,<G> </G>,,,0
<A> </A>,BBA,<B> </B>,,,,,,"A, B, C",
<A> </A>,BBB,,,,,<D> </D>,,,>10
<A> </A>,BBC,,,,,<D> </D>,,,>10
<A> </A>,BBD,<B> </B>,,,,,,"A, B, C, D, Z",
<A> </A>,BBE,<B> </B>,,,,,,"A, B, C, D, E, F, G, H, Z",
<A> </A>,BBF,<B> </B>,,,,,,B,"C, D"
<A> </A>,BBG,,,,,,,,
<A> </A>,BBH,,,,,,,,
"""

from django.test import TestCase
from lizard_progress.util import AutoReviewer
from lizard_progress.util import Observation
from lizard_progress.util import Field

import os


class TestAutoReviewerFromFile(TestCase):

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


class TestAutoReviewerObservation(TestCase):

    def setUp(self):
        self.filterfile = os.path.join('lizard_progress',
                                       'util',
                                       'tests',
                                       'test_autoreviewer_files',
                                       'filter_complete_valid.xlsx')

        self.ar = AutoReviewer(self.ilterfile)

    def test_observations(self):
        # Let's start with single observations
        test_cases = {Observation([Field('A', 'BAA'), Field('B', 'Z'), Field('D', '10')]): 'INTERVENE',
                      Observation([Field('A', 'BAA'), Field('B', 'Z'), Field('D', '6')]): 'WARN',
                      Observation([Field('A', 'BAF'), Field('B', 'Z'), Field('C', 'Z')]): 'WARN',
                      Observation([Field('A', 'BZF'), Field('B', 'Z'), Field('C', 'Z')]): 'NORULE'}

        for obs, expected in test_cases:
            self.assertEquals(self.ar.filterTable.test_observation(obs), expected)
