

from django.test import TestCase

from lizard_progress import models

from lxml import etree


# TODO: set these tests in test_models.py

# lizard_progress.tests.test_review_tool



class TestReviewProject(TestCase):
    """Tests for the ReviewProject model"""

    def setUp(self):
        self.ribx_file = 'lizard_progress/testdata/goed.ribx'
        self.parser = etree.XMLParser()
        self.tree = etree.parse(self.ribx_file)
        self.root = self.tree.getroot()
        self.pr = models.ProjectReview.objects.create()

    def test_create_reviewProject(self):
        pass
        # Create blank ProjectReview
        self.pr.save()

    def test__parse_zb_a(self):
        element = self.root.find('ZB_A')
        pipe = self.pr._parse_zb_a(element)
        self.assertEqual('147715.18 491929.01', pipe['AAE'])
        self.assertEqual('147779.16 491974.99', pipe['AAG'])
        self.assertTrue(set(pipe.keys()).issubset(self.pr.ZB_A_FIELDS))

    def test__parse_zb_c(self):
        element = self.root.find('ZB_C')
        manhole = self.pr._parse_zb_c(element)
        self.assertEqual('146912.77 492728.73', manhole['CAB'])
        self.assertTrue(set(manhole.keys()).issubset(self.pr.ZB_C_FIELDS))

    def test_create_from_ribx(self):
        pr = models.ProjectReview.create_from_ribx(self.ribx_file)
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


