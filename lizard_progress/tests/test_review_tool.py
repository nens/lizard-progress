# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

"""Tests for lizard_progress models.ReviewProject."""

from django.test import TestCase

from lizard_progress import models
from lizard_progress.tests.base import FixturesTestCase
from lizard_progress.tests.test_models import OrganizationF

from lxml import etree

import factory

# TODO: set these tests in test_models.py
# lizard_progress.tests.test_review_tool


class ReviewProjectF(factory.DjangoModelFactory):
    class Meta:
        model = models.ReviewProject

    name = 'Test reviewproject'
    slug = 'testreviewproject'
    organization = factory.SubFactory(OrganizationF)


class TestReviewProject(FixturesTestCase):
    """Tests for the ReviewProject model"""

    def setUp(self):
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

