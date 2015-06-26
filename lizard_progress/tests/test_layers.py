# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

"""Tests for layers.py."""

# Python 3 is coming
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from lizard_progress.tests.base import FixturesTestCase

from lizard_progress.tests import test_models

from lizard_progress import layers


class TestProgressAdapter(FixturesTestCase):
    def test_extent_no_locations(self):
        activity = test_models.ActivityF.create()

        adapter = layers.ProgressAdapter(None, layer_arguments={
            'activity_id': activity.id})

        extent = adapter.extent()
        self.assertEquals(extent['west'], None)
        self.assertEquals(extent['east'], None)
        self.assertEquals(extent['north'], None)
        self.assertEquals(extent['south'], None)

    def test_extent_two_locations(self):
        activity = test_models.ActivityF.create()

        adapter = layers.ProgressAdapter(None, layer_arguments={
            'activity_id': activity.id})

        location1 = test_models.LocationF.create(
            location_code="LOCATION_1",
            activity=activity, the_geom="POINT(150000 450000)")
        location2 = test_models.LocationF.create(
            location_code="LOCATION_2",
            activity=activity, the_geom="POINT(200000 500000)")

        extent = adapter.extent()
