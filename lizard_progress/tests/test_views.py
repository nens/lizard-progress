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
import factory

# lizard_progress.tests.test_views

class TestReviewProjectViews(FixturesTestCase):

    def setUp(self):
        # RIBX test files:
        self.goed_ribx_file_dir = os.path.join('lizard_progress',
                                     'tests',
                                     'test_met_files',
                                     'ribx',
                                     'goed.ribx')

        # Setup test-database with user, organization and reviewproject.
        self.user1 = UserF(username="user1")
        password = 'bad_password'
        self.user1.set_password(password)
        self.organization = OrganizationF(name="testOrganization")
        self.contractor = OrganizationF(name='contractor')
        profile = UserProfileF(user=self.user1,
                               organization=self.organization)
        profile.roles.add(
            models.UserRole.objects.get(
                code=models.UserRole.ROLE_MANAGER))

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
        # Go to new_reviewproject page
        response = self.client.get(reverse('lizard_progress_reviewproject',
                                           kwargs={'review_id': self.reviewproject.id}),
                                   {'user': self.user1})
        self.assertEquals(response.status_code, 200)

    def test_post_invalid_reviewproject(self):
        # Create a invalid reviewproject: no name and no ribx-file
        with open(self.goed_ribx_file_dir) as file:
            response = self.client.post(reverse('lizard_progress_new_reviewproject'),
                                         {'name': '',
                                          'ribx': None
                                          })
            self.assertEquals(response.status_code, 200)
            self.assertTrue(response.context_data['view'].form.errors)
            self.assertIn('name', response.context_data['view'].form.errors)
            self.assertIn('ribx', response.context_data['view'].form.errors)

    def test_post_new_reviewproject_without_filler(self):
        # Create a valid reviewproject without a filler
        with open(self.goed_ribx_file_dir) as file:
            response = self.client.post(reverse('lizard_progress_new_reviewproject'),
                             {'name': 'new reviewproject',
                              'ribx': file,
                              'filler_file': None
                              })
            self.assertEquals(response.status_code, 302)
            self.assertTrue(models.ReviewProject.objects.get(
                name='new reviewproject')
            )

    def test_post_new_reviewproject_with_filler(self):
        # Create a valid reviewproject with a filler, but won't have any
        # matching rules.
        filler_file_path = os.path.join('lizard_progress',
                                   'tests',
                                   'test_met_files',
                                   'filter',
                                   'simple_filter.csv')
        with open(self.goed_ribx_file_dir) as ribx_file, \
            open(filler_file_path) as filler_file:
            response = self.client.post(
                reverse('lizard_progress_new_reviewproject'),
                {'name': 'new reviewproject',
                 'ribx': ribx_file,
                 'filler_file': filler_file
                 })
            self.assertEquals(response.status_code, 302)
            self.assertTrue(models.ReviewProject.objects.get(
                name='new reviewproject')
            )
            reviewProject = models.ReviewProject.objects.get(
                            name='new reviewproject')
            self.assertEquals(reviewProject.calc_progress(), 40)

    def test_post_new_reviewproject_with_filler_applicable(self):
        # Create a valid reviewproject with a filler which should auto-fill
        # some values of the reviews
        filler_file_path = os.path.join('lizard_progress',
                                        'tests',
                                        'test_met_files',
                                        'filter',
                                        'complex_filler.csv')
        with open(self.goed_ribx_file_dir) as ribx_file, \
                open(filler_file_path) as filler_file:
            response = self.client.post(
                reverse('lizard_progress_new_reviewproject'),
                {'name': 'new reviewproject',
                 'ribx': ribx_file,
                 'filler_file': filler_file
                 })
            self.assertEquals(response.status_code, 302)
            self.assertTrue(models.ReviewProject.objects.get(
                name='new reviewproject')
            )
            reviewProject = models.ReviewProject.objects.get(
                            name='new reviewproject')
            self.assertTrue(reviewProject.reviews)
            self.assertTrue(reviewProject.inspection_filler)
            self.assertGreater(reviewProject.calc_progress(), 1)

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
                                        {'reviews': json_file,
                                         'Upload reviews': ''})

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
            # Upload reviews
            response = self.client.post(url,
                                        {'reviews': json_file,
                                         'Upload reviews': ''})

            self.assertEquals(response.status_code, 200)
            self.assertTrue(response.context_data['view'].upload_reviews_form.errors)

    def test_post_new_reviewproject_with_contractor(self):
        filler_file_path = os.path.join('lizard_progress',
                                        'tests',
                                        'test_met_files',
                                        'filter',
                                        'complex_filler.csv')
        with open(self.goed_ribx_file_dir) as ribx_file, \
                open(filler_file_path) as filler_file:
            response = self.client.post(
                reverse('lizard_progress_new_reviewproject'),
                {'name': 'reviewproject with contractor',
                 'ribx': ribx_file,
                 'contractor': self.organization.pk
                 })
            self.assertEquals(response.status_code, 302)
            self.assertTrue(models.ReviewProject.objects.get(
                name='reviewproject with contractor')
            )
            reviewProject = models.ReviewProject.objects.get(
                            name='reviewproject with contractor')
            self.assertTrue(reviewProject.reviews)
            self.assertTrue(reviewProject.contractor)


class ClientFactory(object):

    def __init__(self, role, organization, is_superuser=False):
        username = factory.Sequence(lambda n: 'user{0}'.format(n))
        user = UserF.create(username=username, is_superuser=is_superuser)
        user_profile = UserProfileF.create(user=user, organization=organization)
        user_profile.roles.add(
            models.UserRole.objects.get(code=role))
        password = 'bad_password'
        user.set_password(password)
        user.save()

        self.user_client = Client()
        self.user_client.login(username=user.username,
                               password=password)
        self.user_client.login(username=user.username,
                               password=password)

    @classmethod
    def create(cls, role, organization, is_superuser=False):
        """Creates a user for the organization and returns a client."""
        clientF = cls(role, organization, is_superuser)
        return clientF.user_client


class TestCreateReviewProjectViews(FixturesTestCase):

    def setUp(self):
        organization = OrganizationF.create(name="Organization")
        self.manager_client = ClientFactory.create(
            role=models.UserRole.ROLE_MANAGER,
            organization=organization)
        self.reviewer_client = ClientFactory.create(
            role=models.UserRole.ROLE_REVIEWER,
            organization=organization)
        self.random_client = Client()

    def test_manager_create_reviewproject(self):
        response = self.manager_client.post(
            reverse('lizard_progress_new_reviewproject'), {})
        self.assertEqual(200, response.status_code)

    def test_reviewer_create_reviewproject(self):
        response = self.reviewer_client.post(
            reverse('lizard_progress_new_reviewproject'), {})
        self.assertEqual(403, response.status_code)

    def test_random_create_reviewproject(self):
        response = self.random_client.post(
            reverse('lizard_progress_new_reviewproject'), {})
        self.assertEqual(302, response.status_code)
        self.assertTrue('/accounts/login/' in response.url)


class TestViewDetailReviewProjectViews(FixturesTestCase):

    def setUp(self):
        organization = OrganizationF.create(name="Organization")
        self.reviewproject = ReviewProjectF(organization=organization)
        self.manager_client = ClientFactory.create(
            role=models.UserRole.ROLE_MANAGER,
            organization=organization)
        self.reviewer_client = ClientFactory.create(
            role=models.UserRole.ROLE_REVIEWER,
            organization=organization)
        self.random_client = Client()

    def test_manager_view_project(self):
        response = self.manager_client.get(
            reverse('lizard_progress_reviewproject',
                    kwargs={'review_id': self.reviewproject.id}))
        self.assertEqual(200, response.status_code)

    def test_reviewer_view_project(self):
        response = self.reviewer_client.get(
            reverse('lizard_progress_reviewproject',
                    kwargs={'review_id': self.reviewproject.id}))
        self.assertEqual(200, response.status_code)

    def test_random_view_project(self):
        response = self.random_client.get(
            reverse('lizard_progress_reviewproject',
                    kwargs={'review_id': self.reviewproject.id}))
        self.assertEqual(302, response.status_code)
        self.assertTrue('/accounts/login/' in response.url)


class TestDownloadReviewProjectViews(FixturesTestCase):

    def setUp(self):
        organization = OrganizationF.create(name="Organization")
        self.reviewproject = ReviewProjectF(organization=organization)
        self.manager_client = ClientFactory.create(
            role=models.UserRole.ROLE_MANAGER,
            organization=organization)
        self.reviewer_client = ClientFactory.create(
            role=models.UserRole.ROLE_REVIEWER,
            organization=organization)
        self.random_client = Client()

    def test_manager_download_reviews(self):
        response = self.manager_client.get(
            reverse('lizard_progress_download_reviews',
                    kwargs={'review_id': self.reviewproject.id}))
        self.assertEqual(200, response.status_code)

    def test_reviewer_download_reviews(self):
        response = self.reviewer_client.get(
            reverse('lizard_progress_download_reviews',
                    kwargs = {'review_id': self.reviewproject.id}))
        self.assertEqual(200, response.status_code)

    def test_random_download_reviews(self):
        response = self.random_client.get(
            reverse('lizard_progress_download_reviews',
                    kwargs={'review_id': self.reviewproject.id}))
        self.assertEqual(302, response.status_code)
        self.assertTrue('/accounts/login/' in response.url)


class TestUploadReviewProjectViews(FixturesTestCase):

    def setUp(self):
        orgBeheer = OrganizationF.create(name="Org beheerder")
        orgReview = OrganizationF.create(name="Org reviewer")
        self.reviewproject = ReviewProjectF(organization=orgBeheer,
                                            contractor=orgReview)

        self.manager_client = ClientFactory.create(
            role=models.UserRole.ROLE_MANAGER,
            organization=orgBeheer)
        self.reviewer_client = ClientFactory.create(
            role=models.UserRole.ROLE_REVIEWER,
            organization=orgReview)
        self.random_client = Client()

    def test_manager_upload_reviews(self):
        response = self.manager_client.post(
            reverse('lizard_progress_reviewproject',
                    kwargs={'review_id': self.reviewproject.id}),
            {'Upload reviews': ''})
        self.assertEqual(200, response.status_code)

    def test_reviewer_upload_reviews(self):
        response = self.reviewer_client.post(
            reverse('lizard_progress_reviewproject',
                    kwargs={'review_id': self.reviewproject.id}),
            {'Upload reviews': ''}
        )
        self.assertEqual(200, response.status_code)

    def test_random_upload_reviews(self):
        response = self.random_client.post(
            reverse('lizard_progress_reviewproject',
                    kwargs={'review_id': self.reviewproject.id}),
            {'Upload reviews': ''})
        self.assertEqual(302, response.status_code)
        self.assertTrue('/accounts/login/' in response.url)
