# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

from django.test import TestCase
from django.test import Client
from django.core.urlresolvers import reverse

from lizard_progress import models
from lizard_progress.models import User
from lizard_progress.tests.test_models import UserProfileF
from lizard_progress.tests.test_models import UserF
from lizard_progress.tests.test_models import OrganizationF
from lizard_progress.tests.test_review_tool import ReviewProjectF
from lizard_progress.tests.base import FixturesTestCase

import json
import os

# lizard_progress.tests.test_views

class TestReviewProjectViews(FixturesTestCase):

    def setUp(self):
        # RIBX test files:
        ribx_file_dir = os.path.join('lizard_progress',
                                     'tests',
                                     'test_met_files',
                                     'ribx')
        ribx_files = os.listdir(ribx_file_dir)

        self.abs_path_files = \
            [os.path.join(ribx_file_dir, file) for file in ribx_files]

        # Setup test-database with user, organization and reviewproject.
        self.user1 = UserF(username="user1")
        password = 'bad_password'
        self.user1.set_password(password)
        self.organization = OrganizationF(name="testOrganization")
        UserProfileF(user=self.user1,
                     organization=self.organization)
        self.reviewproject = ReviewProjectF(organization=self.organization)
        self.user1.save()

        self.client = Client()
        self.client.login(username=self.user1.username,
                          password=password)

    def test_get_review_overview(self):
        response = self.client.get(reverse('lizard_progress_reviews_overview'),
                                  {'user': self.user1})
        self.assertEquals(response.status_code, 200)
        reviewprojects = response.context_data['view'].all_review_projects
        self.assertEquals(len(reviewprojects), 1)

    def test_get_reviewproject(self):
        response = self.client.get(reverse('lizard_progress_reviewproject',
                                           kwargs={'review_id': self.reviewproject.id}),
                                   {'user': self.user1})
        self.assertEquals(response.status_code, 200)

    def test_post_new_reviewproject(self):
        # Go to new_reviewproject page
        response = self.client.get(reverse('lizard_progress_new_reviewproject'),
                                   {'user': self.user1})
        self.assertEquals(response.status_code, 200)

        # Create a valid reviewproject
        with open(self.abs_path_files[0]) as file:
            response = self.client.post(reverse('lizard_progress_new_reviewproject'),
                             {'name': 'new reviewproject',
                              'ribx': file
                              })
            self.assertEquals(response.status_code, 302)
            self.assertTrue(models.ReviewProject.objects.get(
                name='new reviewproject')
            )

        # Create a invalid reviewproject: no name and no ribx-file
        response = self.client.post(reverse('lizard_progress_new_reviewproject'),
                                     {'name': '',
                                      'ribx': None
                                      })
        self.assertEquals(response.status_code, 200)
        self.assertTrue(response.context_data['view'].form.errors)
        self.assertIn('name', response.context_data['view'].form.errors)
        self.assertIn('ribx', response.context_data['view'].form.errors)

    def test_upload_valid_reviews(self):
        # Starting with no reviews
        self.assertFalse(self.reviewproject.reviews)
        url = reverse('lizard_progress_reviewproject',
                      kwargs={'review_id': self.reviewproject.id})
        simple_review_path = os.path.join('lizard_progress',
                                          'tests',
                                          'test_met_files',
                                          'review',
                                          'simple.json')
        response = None
        with open(simple_review_path, 'r') as json_file:
            response = self.client.post(url,
                                        {'reviews': json_file})

        self.assertEquals(response.status_code, 302)
        updated_review = models.ReviewProject.objects.get(id=self.reviewproject.id)
        self.assertEquals(updated_review.reviews, json.loads('{"a": "b"}'))

    def test_upload_invalid_reviews(self):
        url = reverse('lizard_progress_reviewproject',
                      kwargs={'review_id': self.reviewproject.id})
        test_file = os.path.join('lizard_progress',
                                 'tests',
                                 'test_met_files',
                                 'review',
                                 'invalid.json')
        response = None
        with open(test_file, 'r') as json_file:
            response = self.client.post(url,
                                        {'reviews': json_file})

        self.assertEquals(response.status_code, 200)
        self.assertTrue(response.context_data['view'].form.errors)



