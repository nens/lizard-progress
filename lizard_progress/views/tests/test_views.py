# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

"""Tests for views/views.py"""

# Python 3 is coming
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division


from django.test import TestCase

import mock

from lizard_progress.views import views
from lizard_progress.tests import test_models


class TestProjectsMixin(TestCase):
    def test_user_without_permission_is_not_manager(self):
        mixin = views.ProjectsMixin()
        mixin.request = mock.MagicMock()
        mixin.request.user = test_models.UserF.create(
            username="testingprojectsmixin", is_superuser=False)

        org = test_models.OrganizationF.create(
            is_project_owner=True)

        test_models.UserProfileF.create(
            user=mixin.request.user,
            organization=org)

        self.assertFalse(mixin.user_is_manager())

    def test_user_with_permission_is_not_manager(self):
        mixin = views.ProjectsMixin()
        mixin.request = mock.MagicMock()
        mixin.request.user = test_models.UserF.create(
            username="testingprojectsmixin", is_superuser=False)

        def custom_has_perm(permission):
            return permission == 'lizard_progress.add_project'

        mixin.request.user.has_perm = custom_has_perm

        org = test_models.OrganizationF.create(
            is_project_owner=True)

        test_models.UserProfileF.create(
            user=mixin.request.user,
            organization=org)

        self.assertTrue(mixin.user_is_manager())
