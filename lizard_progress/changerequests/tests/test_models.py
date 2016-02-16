# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

"""Tests for changerequests models."""

# Python 3 is coming
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import factory

from lizard_progress.tests.base import FixturesTestCase
from lizard_progress.tests import test_models as progresstestmodels
from lizard_progress.changerequests import models


class RequestF(factory.DjangoModelFactory):
    class Meta:
        model = models.Request

    activity = factory.SubFactory(progresstestmodels.ActivityF)

    request_type = models.Request.REQUEST_TYPE_NEW_LOCATION
    request_status = models.Request.REQUEST_STATUS_OPEN

    location_code = 'LOCATION_CODE'


class TestRequest(FixturesTestCase):
    def test_create_deletion_request_works(self):
        location = progresstestmodels.LocationF.create()

        request = models.Request.create_deletion_request(
            location, 'This is a test', False)

        self.assertTrue(request)

    def test_get_old_location(self):
        activity = progresstestmodels.ActivityF.create()
        location1 = progresstestmodels.LocationF.create(
            activity=activity,
            location_code='LOCATION1')
        location2 = progresstestmodels.LocationF.create(
            activity=activity,
            location_code='LOCATION2')

        request = RequestF.create(
            activity=activity,
            request_type=models.Request.REQUEST_TYPE_MOVE_LOCATION,
            location_code=location1.location_code,
            old_location_code=location2.location_code,
            the_geom=location1.the_geom)

        old_location = request.get_old_location()

        self.assertEquals(old_location.pk, location2.pk)
