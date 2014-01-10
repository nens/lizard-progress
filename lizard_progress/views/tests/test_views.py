# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

"""Tests for views/views.py"""

# Python 3 is coming
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division


from django.test import TestCase
from django.test.client import RequestFactory

import mock

from lizard_progress.views import views
from lizard_progress.tests import test_models


class TestMapView(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view = views.MapView.as_view()

    def available_layers_returns_layers(self):
        user = test_models.UserF.create()

