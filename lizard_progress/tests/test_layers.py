# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

"""Tests for layers.py."""

# Python 3 is coming
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from django.test import TestCase

from lizard_progress.tests import test_models

from lizard_progress import layers


class TestProgressAdapter(TestCase):
    def test_extent_no_locations(self):
        project = test_models.ProjectF.create()
        contractor = test_models.ContractorF.create(project=project)

        adapter = layers.ProgressAdapter(None, layer_arguments={
                'project_slug': project.slug,
                'contractor_slug': contractor.slug})

        extent = adapter.extent()
        self.assertEquals(extent['west'], None)
        self.assertEquals(extent['east'], None)
        self.assertEquals(extent['north'], None)
        self.assertEquals(extent['south'], None)

    def test_extent_two_locations(self):
        project = test_models.ProjectF.create()
        contractor = test_models.ContractorF.create(project=project)

        adapter = layers.ProgressAdapter(None, layer_arguments={
                'project_slug': project.slug,
                'contractor_slug': contractor.slug})

        location1 = test_models.LocationF.create(
            location_code="LOCATION_1",
            project=project, the_geom="POINT(150000 450000)")
        location2 = test_models.LocationF.create(
            location_code="LOCATION_2",
            project=project, the_geom="POINT(200000 500000)")

        amt = test_models.AvailableMeasurementTypeF.create()

        mt = test_models.MeasurementTypeF.create(mtype=amt, project=project)

        test_models.ScheduledMeasurementF.create(
            project=project, contractor=contractor, measurement_type=mt,
            location=location1)
        test_models.ScheduledMeasurementF.create(
            project=project, contractor=contractor, measurement_type=mt,
            location=location2)

        extent = adapter.extent()
