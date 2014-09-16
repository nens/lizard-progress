# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

"""Tests for changerequests models."""

# Python 3 is coming
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division


import factory

from lizard_progress.tests import test_models as progresstestmodels
from lizard_progress.changerequests import models


class RequestF(factory.DjangoModelFactory):
    class Meta:
        model = models.Request

    activity = factory.SubFactory(progresstestmodels.ActivityF)
    mtype = factory.LazyAttribute(lambda a: a.activity.measurement_type)
    organization = factory.LazyAttribute(lambda a: a.activity.contractor)

    request_type = models.Request.REQUEST_TYPE_NEW_LOCATION
    request_status = models.Request.REQUEST_STATUS_OPEN

    location_code = 'LOCATION_CODE'
