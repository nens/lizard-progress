# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

"""Tests for lizard_progress util.Filler."""

# lizard_progress.util.tests.test_filler

from django.test import TestCase
from lizard_progress.tests.base import FixturesTestCase

from lizard_progress.util.filler import _flatten_rule
from lizard_progress.util.filler import parse_insp_filler
from lizard_progress.util.filler import build_rule_tree
from lizard_progress.util.filler import _apply_rule
from lizard_progress.util.filler import apply_rules

import json
import os


class TestFlattenRule(FixturesTestCase):

    def setUp(self):
        pass

    def test_aaaa_temp(self):
        # Weird behaviour: django tests does not return good output when the first
        # test case fails when specifying a specific test case. But it does
        # return good output when the first testcase passes. Thus we
        # make sure the testcase passes
        self.assertTrue(True)
        self.assertEquals(1, 1)

    def test_flatten_rule(self):
        valid_simple_rule = ['a', 'b', 'c', 'd', 'e']
        valid_rule_empty_value1 = ['a', '', 'c', 'd', 'e']
        valid_rule_empty_value2 = ['', '', 'c', 'd', 'e']
        valid_rule_empty_value2 = ['', '', 'c', 'd', 'e']
        valid_rule_empty_value3 = ['', '', 'c', 'd', '']
        valid_rule_empty_value4 = ['', '', '', '', '']
        valid_rule_empty_value5 = ['', '', '', '', 'e']

        valid_rule_unflat1 = ['a', 'b, c', 'c', 'd', 'e']
        valid_rule_unflat2 = ['a', 'b, c', 'c, d', 'd', 'e']
        valid_rule_unflat3 = ['a, b', 'b', 'c', 'd, g', 'e, f']

        valid_rule_unflat_with_dupl_values = ['a, a', 'b', 'c', 'd', 'e, e']

        simple_valid_rules = [valid_simple_rule,
                              valid_rule_empty_value1,
                              valid_rule_empty_value2,
                              valid_rule_empty_value3,
                              valid_rule_empty_value4,
                              valid_rule_empty_value5,]

        invalid_rule1 = ['']
        invalid_rule2 = ['a', 'b']
        invalid_rule3 = ['a', 'b', 'c', 'd', 'e', 'f']

        # test valid rules:
        for simple_valid_rule in simple_valid_rules:
            flat_rule = _flatten_rule(simple_valid_rule)
            self.assertEquals(len(flat_rule), 1)
            for el in flat_rule:
                self.assertTrue(',' not in el)

        flat_rules = _flatten_rule(valid_rule_unflat1)
        self.assertEquals(len(flat_rules), 2)
        flat_rules = _flatten_rule(valid_rule_unflat2)
        self.assertEquals(len(flat_rules), 4)
        flat_rules = _flatten_rule(valid_rule_unflat3)
        self.assertEquals(len(flat_rules), 8)

        flat_rules = _flatten_rule(valid_rule_unflat_with_dupl_values)
        self.assertEquals(len(set(flat_rules)), 1)

        # test invalid rules:
        with self.assertRaises(AssertionError):
            _flatten_rule(invalid_rule1)
            _flatten_rule(invalid_rule2)
            _flatten_rule(invalid_rule3)


class TestRuleTree(FixturesTestCase):

    def setUp(self):
        self.filler_files = os.path.join('lizard_progress',
                                         'util',
                                         'tests',
                                         'test_filler_files',
                                         'fillers')

    def test_build_rule_tree_from_simple_filler(self):
        filler_simple = 'simple_filler.csv'
        filler_simple_file = os.path.join(self.filler_files, filler_simple)
        with open(filler_simple_file) as filler:
            rules = parse_insp_filler(filler)

            self.assertEquals(len(rules), 4)

            rule_tree = build_rule_tree(rules)

            self.assertEquals(len(rule_tree.keys()), 2)
            self.assertTrue(len(rule_tree['a']), 1)
            self.assertTrue(len(rule_tree['b']), 2)
            self.assertTrue(len(rule_tree['b']['b']), 2)

    def test_apply_rule(self):
        filler_simple = 'simple_filler.csv'
        filler_simple_file = os.path.join(self.filler_files, filler_simple)
        with open(filler_simple_file) as filler:
            rules = parse_insp_filler(filler)
            rule_tree = build_rule_tree(rules)
            zc_empty = {'A': '',
                        'B': '',
                        'C': '',
                        'D': '',
                        'Herstelmaatregel': '',
                        'Opmerking': ''}
            result = _apply_rule(rule_tree, zc_empty)
            self.assertEquals('', result['Herstelmaatregel'])

            zc_waarschuwing = {'A': 'a',
                        'B': 'b',
                        'C': 'c',
                        'D': 'd',
                        'Herstelmaatregel': '',
                        'Opmerking': ''}
            result = _apply_rule(rule_tree, zc_waarschuwing)
            self.assertEquals('waarschuwing', result['Herstelmaatregel'])

            zc_ingrijp = {'A': 'a',
                          'B': 'b',
                          'C': 'c',
                          'D': 'f',
                          'Herstelmaatregel': '',
                          'Opmerking': ''}
            result = _apply_rule(rule_tree, zc_ingrijp)
            self.assertEquals('ingrijp', result['Herstelmaatregel'])

            zc_skip = {'A': 'a',
                          'B': 'b',
                          'C': 'c',
                          'D': 'f',
                          'Herstelmaatregel': 'aaa',
                          'Opmerking': ''}
            result = _apply_rule(rule_tree, zc_skip)
            self.assertEquals('aaa', result['Herstelmaatregel'])

    def test_apply_rule_with_empty_rules(self):
        filler_unflat = 'unflattenned_filler.csv'
        filler_unflat_file = os.path.join(self.filler_files, filler_unflat)
        with open(filler_unflat_file) as filler:
            rules = parse_insp_filler(filler)
            rule_tree = build_rule_tree(rules)
            zc_waarschuwing = {'A': 'a',
                        'B': 'c',
                        'C': 'c',
                        'D': 'd',
                        'Herstelmaatregel': '',
                        'Opmerking': ''}
            result = _apply_rule(rule_tree, zc_waarschuwing)
            self.assertEquals('waarschuwing', result['Herstelmaatregel'])

            zc_with_empty = {'A': 'b',
                               'B': 'f',
                               'C': '',
                               'D': 'g',
                               'Herstelmaatregel': '',
                               'Opmerking': ''}
            result = _apply_rule(rule_tree, zc_with_empty)
            self.assertEquals('ingrijp', result['Herstelmaatregel'])
