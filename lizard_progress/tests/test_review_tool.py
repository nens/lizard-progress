# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

"""Tests for lizard_progress models.ReviewProject."""

from django.test import TestCase

from lizard_progress import models
from lizard_progress.tests.base import FixturesTestCase
from lizard_progress.tests.test_models import OrganizationF

from lxml import etree

import factory
import json
import os
import csv

# TODO: set these tests in test_models.py
# lizard_progress.tests.test_review_tool


class ReviewProjectF(factory.DjangoModelFactory):
    class Meta:
        model = models.ReviewProject

    name = 'Test reviewproject'
    slug = factory.Sequence(lambda n: 'testreviewproject%d' % n)
    organization = factory.SubFactory(OrganizationF)
    reviews = None


class TestReviewProject(FixturesTestCase):
    """Tests for the ReviewProject model"""

    def setUp(self):
        self.test_files = os.path.join('lizard_progress',
                                       'tests',
                                       'test_met_files')
        self.name = 'Test reviewproject'
        self.ribx_file = 'lizard_progress/tests/test_met_files/ribx/goed.ribx'
        self.single_pipe = 'lizard_progress/tests/test_met_files/ribx/single_pipe.ribx'
        self.single_manhole = 'lizard_progress/tests/test_met_files/ribx/single_manhole.ribx'

        self.organization = models.Organization.objects.create(
            name='Test organization'
        )
        self.pr = models.ReviewProject.objects.create(
            name='Test reviewproject',
            organization=self.organization)

    def test_create_reviewProject(self):
        # Create blank ReviewProject
        self.pr.save()

    def test_set_slug_and_save(self):
        organization = self.organization
        pr = self.pr
        pr.set_slug_and_save()
        self.assertTrue(pr.slug)
        self.assertTrue(unicode(pr.id) in pr.slug)
        self.assertTrue('test-reviewproject' in pr.slug)

    def test__parse_zb_a(self):
        tree = etree.parse(self.single_pipe)
        root = tree.getroot()
        element = root.find('ZB_A')
        pipe = self.pr._parse_zb_a(element)
        self.assertEqual('147715.18 491929.01', pipe['AAE'])
        self.assertEqual('147779.16 491974.99', pipe['AAG'])
        self.assertTrue(set(pipe.keys()).issubset(self.pr.ZB_A_FIELDS))
        self.assertEquals(len(pipe['ZC']), 2)

    def test__parse_zb_c(self):
        tree = etree.parse(self.single_manhole)
        root = tree.getroot()
        element = root.find('ZB_C')
        manhole = self.pr._parse_zb_c(element)
        self.assertEqual('146916.82 492326.42', manhole['CAB'])
        self.assertTrue(set(manhole.keys()).issubset(self.pr.ZB_C_FIELDS))

    def test__parse_zc(self):
        tree = etree.parse(self.single_pipe)
        root = tree.getroot()
        element = root.find('ZB_A').find('ZC')
        inspection = self.pr._parse_zc(element)
        self.assertTrue(inspection.has_key('Herstelmaatregel'))
        self.assertTrue(inspection.has_key('Opmerking'))

    def test_create_from_ribx(self):
        pr = models.ReviewProject.create_from_ribx(self.name,
                                                   self.ribx_file,
                                                   self.organization)
        reviews = pr.reviews
        pipes = reviews['pipes']
        man_holes = reviews['manholes']

        self.assertEqual(len(pipes), 4)
        self.assertEqual(len(man_holes), 6)

        self.assertEqual('147715.18 491929.01', pipes[0]['AAE'])
        self.assertEqual('147779.16 491974.99', pipes[0]['AAG'])
        self.assertEqual('146912.77 492728.73', man_holes[0]['CAB'])

        self.assertTrue(set(pipes[0].keys()).issubset(pr.ZB_A_FIELDS))
        self.assertTrue(set(man_holes[0].keys()).issubset(pr.ZB_C_FIELDS))

    def test__manholes_to_points(self):
        pr = models.ReviewProject.create_from_ribx(self.name,
                                                   self.single_manhole,
                                                   self.organization)
        geo_manholes = pr._manholes_to_points()
        self.assertTrue(geo_manholes.is_valid)
        self.assertEquals(len(geo_manholes.get('coordinates')), 1)

    def test__pipes_to_lines(self):
        pr = models.ReviewProject.create_from_ribx(self.name,
                                                   self.single_pipe,
                                                   self.organization)
        geo_pipes = pr._pipes_to_lines()
        self.assertTrue(geo_pipes.is_valid)

    def test_generate_geojson_reviews(self):
        pr = models.ReviewProject.create_from_ribx(self.name,
                                                   self.ribx_file,
                                                   self.organization)
        geojson = pr.generate_geojson_reviews()
        self.assertTrue(geojson.is_valid)
        self.assertEquals(len(geojson['geometries'][0]['coordinates']), 6)
        self.assertEquals(len(geojson['geometries'][1]['coordinates']), 4)

    def test_generate_feature_collection(self):
        pr = models.ReviewProject.create_from_ribx(self.name,
                                                   self.ribx_file,
                                                   self.organization)
        geojson = pr.generate_feature_collection()
        self.assertTrue(geojson.is_valid)
        self.assertEquals(len(geojson.features), 10)

    def _calc_progress_manhole(self, manhole):
        progress = self.pr._calc_progress_manhole(manhole)
        self.assertEquals(progress, 0.0)

    def _calc_progress_pipe(self, pipe):
        progress = self.pr._calc_progress_pipe(pipe)
        self.assertEquals(progress, 1.0)

    def test_calc_progress(self):
        review_file = os.path.join(self.test_files,
                                   'review',
                                   'review_uncompleted.json')
        with open(review_file) as json_file:
            review = ReviewProjectF(reviews=json.load(json_file))
            uncompleted_manhole = review.reviews['manholes'][0]
            self._calc_progress_manhole(uncompleted_manhole)
            uncompleted_pipe = review.reviews['pipes'][0]
            self._calc_progress_pipe(uncompleted_pipe)

            total_progress = review.calc_progress()
            self.assertEquals(total_progress, 0.375)

    def test_flatten_rule(self):
        unflattenned_filter = 'unflattenned_filter.csv'
        filter_file = os.path.join(self.test_files,
                                  'filter',
                                  unflattenned_filter)
        with open(filter_file) as csvfile:
            reader = csv.reader(csvfile)
            simple_rule = reader.next()
            unflat_rule = reader.next()
            empty_field_rule = reader.next()

            flat_simple_rules = list(self.pr._flatten_rule(simple_rule))
            self.assertEquals(len(flat_simple_rules), 1)
            # a rule contains 5 elements
            self.assertEquals(len(flat_simple_rules[0]), 5)
            for el in simple_rule[0]:
                self.assertTrue(',' not in el)

            flat_unflat_rules = list(self.pr._flatten_rule(unflat_rule))
            self.assertEquals(len(flat_unflat_rules), 6)

            flat_empty_field_rules = list(self.pr._flatten_rule(empty_field_rule))
            self.assertEquals(len(flat_empty_field_rules), 2)

    def test_build_rule_tree(self):
        simple_filter = 'simple_filter.csv'
        filter_file = os.path.join(self.test_files, 'filter', simple_filter)
        with open(filter_file) as csvfile:
            inspection_rules = self.pr.parse_filter(csvfile)
            self.assertEquals(len(inspection_rules), 4)

            rule_tree = self.pr.build_rule_tree(inspection_rules)
            self.assertEquals(len(rule_tree.keys()), 2)
            self.assertTrue(len(rule_tree['a']), 1)
            self.assertTrue(len(rule_tree['b']), 2)
            self.assertTrue(len(rule_tree['b']['b']), 2)

    def test_apply_filter(self):
        pass

