# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

"""Tests for lizard_progress util.Filler."""


from django.test import TestCase
from lizard_progress.tests.base import FixturesTestCase

from lizard_progress.util.filler import _flatten_rule
from lizard_progress.util.filler import parse_insp_filler
from lizard_progress.util.filler import build_rule_tree
from lizard_progress.util.filler import _apply_rule
from lizard_progress.util.filler import apply_rules

import json
import os

# lizard_progress.util.tests.test_filler


class TestFlattenRule(FixturesTestCase):

    def setUp(self):
        pass

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

            self.assertEquals(len(rules), 5)

            rule_tree = build_rule_tree(rules)

            self.assertEquals(len(rule_tree.keys()), 3)
            self.assertTrue(len(rule_tree['a']), 1)
            self.assertTrue(len(rule_tree['b']), 2)
            self.assertTrue(len(rule_tree['b']['b']), 1)

class TestApplyRuleSimple(FixturesTestCase):

    def setUp(self):
        self.filler_files = os.path.join('lizard_progress',
                                         'util',
                                         'tests',
                                         'test_filler_files',
                                         'fillers')
        filler_simple = 'simple_filler.csv'
        filler_simple_file = os.path.join(self.filler_files, filler_simple)
        self.rule_tree = None
        with open(filler_simple_file) as filler:
            rules = parse_insp_filler(filler)
            self.rule_tree = build_rule_tree(rules)

    def test_apply_rule_empty_zc(self):
        zc_empty = {'A': '',
                    'B': '',
                    'C': '',
                    'D': '',
                    'Herstelmaatregel': '',
                    'Opmerking': ''}
        result = _apply_rule(self.rule_tree, zc_empty)
        self.assertEquals('', result['Herstelmaatregel'])

    def test_apply_simple_rule_waarschuwing(self):
        zc_waarschuwing = {'A': 'a',
                    'B': 'b',
                    'C': 'c',
                    'D': 'd',
                    'Herstelmaatregel': '',
                    'Opmerking': ''}
        result = _apply_rule(self.rule_tree, zc_waarschuwing)
        self.assertEquals('waarschuwing', result['Herstelmaatregel'])

    def test_apply_simple_rule_ingrijp(self):
        zc_ingrijp = {'A': 'a',
                      'B': 'b',
                      'C': 'c',
                      'D': 'f',
                      'Herstelmaatregel': '',
                      'Opmerking': ''}
        result = _apply_rule(self.rule_tree, zc_ingrijp)
        self.assertEquals('ingrijp', result['Herstelmaatregel'])

    def test_apply_simple_rule_already_filled_zc(self):
        # rule should skip because zc has already been filled in
        zc_skip = {'A': 'a',
                   'B': 'b',
                   'C': 'c',
                   'D': 'f',
                   'Herstelmaatregel': 'aaa',
                   'Opmerking': ''}
        result = _apply_rule(self.rule_tree, zc_skip)
        self.assertEquals('aaa', result['Herstelmaatregel'])

    def test_apply_rule_with_empty_rules(self):
        zc_waarschuwing = {'A': 'b',
                    'B': '',
                    'C': '',
                    'D': 'h',
                    'Herstelmaatregel': '',
                    'Opmerking': ''}
        result = _apply_rule(self.rule_tree, zc_waarschuwing)
        self.assertEquals('waarschuwing', result['Herstelmaatregel'])

    def test_general_rule(self):
        zc_ingrijp = {'A': 'c',
                           'B': '',
                           'C': '',
                           'D': '0',
                           'Herstelmaatregel': '',
                           'Opmerking': ''}
        result = _apply_rule(self.rule_tree, zc_ingrijp)
        self.assertEquals('ingrijp', result['Herstelmaatregel'])


class TestApplyRuleComplex(FixturesTestCase):

    def setUp(self):
        self.filler_files = os.path.join('lizard_progress',
                                         'util',
                                         'tests',
                                         'test_filler_files',
                                         'fillers')
        filler_complex = 'complex_filler.csv'
        filler_complex_file = os.path.join(self.filler_files, filler_complex)
        self.rule_tree = None
        with open(filler_complex_file) as filler:
            rules = parse_insp_filler(filler)
            self.rule_tree = build_rule_tree(rules)

    def test_apply_rule_waarschuwing(self):
        zc_waarschuwing = {'A': 'a',
                           'B': 'b',
                           'C': 'c',
                           'D': '3',
                           'Herstelmaatregel': '',
                           'Opmerking': ''}
        result = _apply_rule(self.rule_tree, zc_waarschuwing)
        self.assertEquals('waarschuwing', result['Herstelmaatregel'])

    def test_apply_rule_ingrijp(self):
        zc_ingrijp = {'A': 'a',
                      'B': 'b',
                      'C': 'c',
                      'D': '7',
                      'Herstelmaatregel': '',
                      'Opmerking': ''}
        result = _apply_rule(self.rule_tree, zc_ingrijp)
        self.assertEquals('ingrijp', result['Herstelmaatregel'])

    def test_apply_rule_ingrijp_smaller(self):
        zc_ingrijp = {'A': 'b',
                      'B': 'b',
                      'C': 'c2',
                      'D': '-2',
                      'Herstelmaatregel': '',
                      'Opmerking': ''}
        result = _apply_rule(self.rule_tree, zc_ingrijp)
        self.assertEquals('ingrijp', result['Herstelmaatregel'])

    def test_apply_rule_simple_complex(self):
        # a rule with both '>' and 'a'
        zc_ingrijp = {'A': 'c',
                      'B': 'd',
                      'C': 'e',
                      'D': '6',
                      'Herstelmaatregel': '',
                      'Opmerking': ''}
        result = _apply_rule(self.rule_tree, zc_ingrijp)
        self.assertEquals('ingrijp', result['Herstelmaatregel'])

    def test_apply_rule_simple_complex_waarschuwing(self):
        # a rule with both '>' and 'a'
        zc_waarschuwing = {'A': 'c',
                           'B': 'd',
                           'C': 'e',
                           'D': 'a',
                           'Herstelmaatregel': '',
                           'Opmerking': ''}
        result = _apply_rule(self.rule_tree, zc_waarschuwing)
        self.assertEquals('waarschuwing', result['Herstelmaatregel'])

    def test_apply_rule_simple_complex_ingrijp(self):
        # a rule with both '>' and 'a'
        zc_ingrijp = {'A': 'c',
                           'B': 'd',
                           'C': 'e',
                           'D': '10.00',
                           'Herstelmaatregel': '',
                           'Opmerking': ''}
        result = _apply_rule(self.rule_tree, zc_ingrijp)
        self.assertEquals('ingrijp', result['Herstelmaatregel'])

    def test_apply_rule_complex_simple_waarschuwing(self):
        # a rule with both 'a' and '<'
        zc_waarschuwing = {'A': 'c',
                           'B': 'd',
                           'C': 'f',
                           'D': '4.4',
                           'Herstelmaatregel': '',
                           'Opmerking': ''}
        result = _apply_rule(self.rule_tree, zc_waarschuwing)
        self.assertEquals('waarschuwing', result['Herstelmaatregel'])

    def test_apply_rule_complex_simple_ingrijp(self):
        # a rule with both 'a' and '<'
        zc_ingrijp = {'A': 'c',
                       'B': 'd',
                       'C': 'f',
                       'D': 'b',
                       'Herstelmaatregel': '',
                       'Opmerking': ''}
        result = _apply_rule(self.rule_tree, zc_ingrijp)
        self.assertEquals('ingrijp', result['Herstelmaatregel'])

    def test_overriding_rule(self):
        zc_waarschuwing = {'A': 'd',
                      'B': 'e',
                      'C': 'f',
                      'D': 'g',
                      'Herstelmaatregel': '',
                      'Opmerking': ''}
        result = _apply_rule(self.rule_tree, zc_waarschuwing)
        self.assertEquals('waarschuwing', result['Herstelmaatregel'])

        zc_waarschuwing = {'A': 'd',
                           'B': 'e',
                           'C': 'f',
                           'D': 'h',
                           'Herstelmaatregel': '',
                           'Opmerking': ''}
        result = _apply_rule(self.rule_tree, zc_waarschuwing)
        self.assertEquals('waarschuwing', result['Herstelmaatregel'])

    def test_overriding_rule2(self):
        zc_waarschuwing = {'A': 'c',
                      'B': 'd',
                      'C': 'f',
                      'D': '4',
                      'Herstelmaatregel': '',
                      'Opmerking': ''}
        result = _apply_rule(self.rule_tree, zc_waarschuwing)
        self.assertEquals('waarschuwing', result['Herstelmaatregel'])

        zc_ingrijp = {'A': 'c',
                       'B': 'd',
                       'C': 'f',
                       'D': '-0.4',
                       'Herstelmaatregel': '',
                       'Opmerking': ''}
        result = _apply_rule(self.rule_tree, zc_ingrijp)
        self.assertEquals('ingrijp', result['Herstelmaatregel'])


class TestApplyRuleRemove(FixturesTestCase):

    def setUp(self):
        self.filler_files = os.path.join('lizard_progress',
                                         'util',
                                         'tests',
                                         'test_filler_files',
                                         'fillers')
        filler_remove = 'filler_with_remove.csv'
        filler_remove_file = os.path.join(self.filler_files, filler_remove)
        self.rule_tree = None
        with open(filler_remove_file) as filler:
            rules = parse_insp_filler(filler)
            self.rule_tree = build_rule_tree(rules)

    def test_apply_rule_without_remove(self):
        zc_waarschuwing = {'A': 'c',
                           'B': 'd',
                           'C': 'c',
                           'D': '4',
                           'Herstelmaatregel': '',
                           'Opmerking': ''}
        result = _apply_rule(self.rule_tree, zc_waarschuwing)
        self.assertEquals('waarschuwing', result['Herstelmaatregel'])

    def test_apply_rule_remove_specific(self):
        zc_remove = {'A': 'c',
                     'B': 'd',
                     'C': 'e',
                     'D': '4',
                     'Herstelmaatregel': '',
                     'Opmerking': ''}
        result = _apply_rule(self.rule_tree, zc_remove)
        self.assertIsNone(result)

    def test_apply_rule_remove_general(self):
        zc_remove = {'A': 'c',
                     'B': 'd',
                     'C': '',
                     'D': '4',
                     'Herstelmaatregel': '',
                     'Opmerking': ''}
        result = _apply_rule(self.rule_tree, zc_remove)
        self.assertIsNone(result)

    def test_apply_rule_remove_more_general(self):
        zc_remove = {'A': 'c',
                     'B': '',
                     'C': '',
                     'D': '',
                     'Herstelmaatregel': '',
                     'Opmerking': ''}
        result = _apply_rule(self.rule_tree, zc_remove)
        self.assertIsNone(result)

    def test_apply_rule_remove_at_wrong_place(self):
        zc_remove = {'A': 'd',
                     'B': '',
                     'C': '',
                     'D': '',
                     'Herstelmaatregel': '',
                     'Opmerking': ''}
        result = _apply_rule(self.rule_tree, zc_remove)
        self.assertIsNotNone(result)
        self.assertEquals(result, zc_remove)


class TestApplyFiller(FixturesTestCase):

    def setUp(self):
        self.filler_files = os.path.join('lizard_progress',
                                         'util',
                                         'tests',
                                         'test_filler_files',
                                         'fillers')
        self.review_files = os.path.join('lizard_progress',
                                         'util',
                                         'tests',
                                         'test_filler_files',
                                         'reviews')
        simple_filler_file = os.path.join(self.filler_files, 'simple_filler.csv')
        with open(simple_filler_file) as filler:
            rules = parse_insp_filler(filler)
            self.rule_tree_simple = build_rule_tree(rules)

        filler_complex_file2 = os.path.join(self.filler_files, 'complex_filler2.csv')
        with open(filler_complex_file2) as filler:
            rules = parse_insp_filler(filler)
            self.rule_tree_complex2 = build_rule_tree(rules)

        review_complex_file = os.path.join(self.review_files, 'complex_review.json')
        with open(review_complex_file) as review:
            self.review_complex = json.load(review)

    def test_apply_filler_simple(self):
        simple_reviews = """{
                  "manholes": [],
                  "pipes": [
                      {
                          "AAA": "3100036",
                          "Herstelmaatregel": "",
                          "Opmerking": "",
                          "ZC": [
                              {
                                  "A": "a",
                                  "B": "b",
                                  "C": "c",
                                  "D": "d",
                                  "Herstelmaatregel": "",
                                  "I": "0",
                                  "N": "3100036.mpg|00:00:00",
                                  "Opmerking": ""
                              },
                              {
                                  "A": "c",
                                  "B": "",
                                  "D": "0",
                                  "F": "Camera",
                                  "Herstelmaatregel": "",
                                  "I": "0.01",
                                  "N": "3100036.mpg",
                                  "Opmerking": ""
                              }
                          ]
                      }
        	]
        }"""
        reviews = json.loads(simple_reviews)
        result = apply_rules(self.rule_tree_simple, reviews)
        self.assertEquals(len(result['pipes']), 1)
        self.assertEquals(len(result['pipes'][0]['ZC']), 2)
        self.assertEquals(result['pipes'][0]['ZC'][0]['Herstelmaatregel'],
                          'waarschuwing')
        self.assertEquals(result['pipes'][0]['ZC'][1]['Herstelmaatregel'],
                          'ingrijp')

    def test_apply_filler_with_removal(self):
        reviews = """
        {
          "manholes": [],
          "pipes": 
          [
              {
                  "AAA": "3100036",
                  "Herstelmaatregel": "",
                  "Opmerking": "",
                  "ZC": [
                      {
                          "A": "a",
                          "B": "b",
                          "C": "c",
                          "D": "d",
                          "Herstelmaatregel": "",
                          "I": "0",
                          "N": "3100036.mpg|00:00:00",
                          "Opmerking": ""
                      },
                      {
                          "A": "c",
                          "B": "",
                          "D": "3",
                          "F": "Camera",
                          "Herstelmaatregel": "",
                          "I": "0.01",
                          "N": "3100036.mpg",
                          "Opmerking": ""
                      }
                  ]
              },
              { 
                  "AAA": "3100036",
                  "Herstelmaatregel": "",
                  "Opmerking": "",
                  "ZC": [
                  {
                      "A": "a",
                      "B": "d",
                      "C": "c",
                      "D": "d",
                      "Herstelmaatregel": "",
                      "I": "0",
                      "N": "3100036.mpg|00:00:00",
                      "Opmerking": ""
                  },
                  {
                      "A": "a",
                      "B": "",
                      "F": "Camera",
                      "Herstelmaatregel": "",
                      "I": "0.01",
                      "N": "3100036.mpg",
                      "Opmerking": ""
                  }
                ]
              }
          ]	
        }"""
        reviews = json.loads(reviews)
        result = apply_rules(self.rule_tree_complex2, reviews)
        self.assertEquals(len(result['pipes'][0]['ZC']), 1)
        self.assertEquals(result['pipes'][0]['ZC'][0]['Herstelmaatregel'],
                          'waarschuwing')
        self.assertEquals(len(result['pipes'][1]['ZC']), 1)
        self.assertEquals(result['pipes'][1]['ZC'][0]['Herstelmaatregel'], '')

    def test_apply_filler_remove_all_inspections(self):
        reviews = """
        {
          "manholes": [],
          "pipes": 
          [
              {
                  "AAA": "3100036",
                  "Herstelmaatregel": "",
                  "Opmerking": "",
                  "ZC": [
                      {
                          "A": "a",
                          "B": "",
                          "Herstelmaatregel": "",
                          "I": "0",
                          "N": "3100036.mpg|00:00:00",
                          "Opmerking": ""
                      }
                  ]
              }
          ]	
        }"""
        reviews = json.loads(reviews)
        result = apply_rules(self.rule_tree_complex2, reviews)
        self.assertEquals(len(result['pipes'][0]['ZC']), 0)
