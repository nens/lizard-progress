# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

"""Tests for lizard_progress util.AutoReviewer
Content of the test filter file (converted to CSV):

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

from lizard_progress.util.autoreviewer import AutoReviewer
from lizard_progress.util.autoreviewer import Observation
from lizard_progress.util.autoreviewer import Field
from lizard_progress.models import ReviewProject
from lizard_progress.tests.test_models import OrganizationF
from lizard_progress.tests.base import FixturesTestCase

import os
import factory


class ReviewProjectF(factory.DjangoModelFactory):
    class Meta:
        model = ReviewProject

    name = 'Test reviewproject'
    slug = factory.Sequence(lambda n: 'testreviewproject%d' % n)
    organization = factory.SubFactory(OrganizationF)
    contractor = None
    reviews = None
    inspection_filler = None


class TestAutoReviewerFromFile(FixturesTestCase):

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


class TestAutoReviewerObservation(FixturesTestCase):

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
                      Observation([Field('A', 'BBB'), Field('D', '4'), Field('F', '6')]): 'WARN',
                      Observation([Field('A', 'BBB'), Field('D', '13'), Field('H', '6')]): 'INTERVENE',
                      Observation([Field('A', 'BAF'), Field('B', 'Z'), Field('C', 'Z')]): 'WARN',
                      Observation([Field('A', 'BZF'), Field('B', 'Z'), Field('C', 'Z')]): 'NORULE',
                      Observation([Field('A', 'BAO'), Field('R', '0'), Field('G', '1')]): 'NOACTION',
                      Observation([Field('A', 'BAO'), Field('R', '0'), Field('G', '0')]): 'INTERVENE'}

        for obs, expected in test_cases:
            self.assertEquals(self.ar.filterTable.test_observation(obs), expected)


class TestAutoReviewerRIBX(FixturesTestCase):
    def setUp(self):
        self.filterfile = os.path.join('lizard_progress',
                                       'util',
                                       'tests',
                                       'test_autoreviewer_files',
                                       'filter_complete_valid.xlsx')

        self.ar = AutoReviewer(self.filterfile)

        self.ribx = os.path.join('lizard_progress',
                                 'util',
                                 'tests',
                                 'test_autoreviewer_files',
                                 'testbestand_metingen.ribx')

    def test_ribx_result(self):
        # test reviews based on a ribx file and a xlsx filter file
        with self.settings(CELERY_ALWAYS_EAGER=True,
                           CELERY_EAGER_PROPAGATES_EXCEPTIONS=True):
            pr = ReviewProject.create_from_ribx('test RP name',
                                                self.ribx,
                                                'test organization name',
                                                inspection_filler=self.filterfile,
                                                move=False)

        pr = ReviewProject.objects.get(pk=pr.pk)  # Refresh

        self.assertIsNotNone(pr.reviews)

        rev_pipes = pr.reviews['pipes']

        for pipe in rev_pipes:

            for zc in pipe['ZC']:

                if zc['A'] == 'BAA':
                    if zc['D'] > 10:
                        self.assertEquals(zc['Herstelmaatregel'], 'Ingrijp')
                    elif zc['D'] > 5:
                        self.assertEquals(zc['Herstelmaatregel'], 'Waarschuwing')
                    else:
                        self.assertEquals(zc['Herstelmaatregel'], '')

                elif zc['A'] == 'BAB':
                    if zc['B'] in ['B', 'C']:
                        self.assertEquals(zc['Herstelmaatregel'], 'Waarschuwing')
                    else:
                        self.assertEquals(zc['Herstelmaatregel'], '')

                elif zc['A'] == 'BAC':
                    if zc['B'] in ['B', 'C']:
                        self.assertEquals(zc['Herstelmaatregel'], 'Ingrijp')
                    elif zc['B'] == 'A':
                        self.assertEquals(zc['Herstelmaatregel'], 'Waarschuwing')
                    else:
                        self.assertEquals(zc['Herstelmaatregel'], '')

                elif zc['A'] in ['BAD', 'BAE']:
                    self.assertEquals(zc['Herstelmaatregel'], '')

                elif zc['A'] == 'BAF':
                    if zc['B'] in 'EFGI' and zc['C'] == 'A':
                        self.assertEquals(zc['Herstelmaatregel'], 'Waarschuwing')
                    elif zc['B'] in 'CDEFGHI' and zc['C'] == 'B':
                        self.assertEquals(zc['Herstelmaatregel'], 'Waarschuwing')
                    elif zc['B'] in 'CDEFGHI' and zc['C'] in 'CD':
                        self.assertEquals(zc['Herstelmaatregel'], 'Waarschuwing')
                    elif zc['B'] and zc['C']in 'EZ':
                        self.assertEquals(zc['Herstelmaatregel'], 'Waarschuwing')
                    else:
                        self.assertEquals(zc['Herstelmaatregel'], '')

                elif zc['A'] == 'BAG':
                    if float(zc['D']) > 25:
                        self.assertEquals(zc['Herstelmaatregel'], 'Waarschuwing')
                    else:
                        self.assertEquals(zc['Herstelmaatregel'], '')

                elif zc['A'] == 'BAH':
                    if zc['B'] in 'EZ':
                        self.assertEquals(zc['Herstelmaatregel'], 'Waarschuwing')
                    else:
                        self.assertEquals(zc['Herstelmaatregel'], '')

                elif zc['A'] == 'BAI':
                    if zc['B'] == 'A' and zc['C'] in 'BCD':
                        self.assertEquals(zc['Herstelmaatregel'], 'Waarschuwing')
                    else:
                        self.assertEquals(zc['Herstelmaatregel'], '')

                elif zc['A'] == 'BAJ':
                    if zc['B'] == 'B' and int(zc['D']) == 10:
                        self.assertEquals(zc['Herstelmaatregel'], 'Waarschuwing')
                    else:
                        self.assertEquals(zc['Herstelmaatregel'], '')

                elif zc['A'] == 'BAK':
                    if zc['B'] in 'ABCEFGHIJK':
                        self.assertEquals(zc['Herstelmaatregel'], 'Waarschuwing')
                    else:
                        self.assertEquals(zc['Herstelmaatregel'], '')

                elif zc['A'] in ['BAL', 'BAM', 'BAN']:
                    self.assertEquals(zc['Herstelmaatregel'], '')

                elif zc['A'] in ['BAO', 'BAP']:
                    if int(zc['G']) == 0:
                        self.assertEquals(zc['Herstelmaatregel'], 'Ingrijp')
                    else:
                        self.assertEquals(zc['Herstelmaatregel'], '')

                elif zc['A'] == 'BBA':
                    if zc['B'] in 'ABC':
                        self.assertEquals(zc['Herstelmaatregel'], 'Waarschuwing')
                    else:
                        self.assertEquals(zc['Herstelmaatregel'], '')
