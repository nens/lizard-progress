# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

"""Adapter that shows change requests on the map, and allows accepting
them in a popup."""

# Python 3 is coming
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import logging
import math

import mapnik
from pkg_resources import resource_filename  # pylint: disable=E0611

from django.template import RequestContext
from django.template.loader import render_to_string

from lizard_map.coordinates import RD
from lizard_map.coordinates import google_to_rd
from lizard_map.coordinates import rd_to_google
from lizard_map.workspace import WorkspaceItemAdapter

from lizard_progress.layers import mapnik_datasource
from lizard_progress import models as pmodels

from . import models

logger = logging.getLogger(__name__)

COLOR_NEW = "blue"
COLOR_OLD = "black"


class ChangeRequestAdapter(WorkspaceItemAdapter):
    def __init__(self, *args, **kwargs):
        if ('layer_arguments' not in kwargs or
            not isinstance(kwargs['layer_arguments'], dict)):
            raise ValueError(
                'Argument layer_arguments of adapter should be a dict.')

        self.changerequest_id = kwargs['layer_arguments']['changerequest_id']

        self.changerequest = models.Request.objects.get(
            pk=self.changerequest_id)

        # We only work for open change requests.
        if not self.changerequest.is_open:
            self.changerequest = None

        super(ChangeRequestAdapter, self).__init__(*args, **kwargs)

    def layer_desc(self, color=COLOR_NEW):
        if color == COLOR_OLD:
            return b"Oude of te verwijderen locatie"

        desc = unicode(self.changerequest)
        return desc.encode('utf8')

    def symbol_img(self, img_file):
        return (
            resource_filename(
                "lizard_progress",
                ("/static/lizard_progress/%s" % img_file)).encode('utf8'),
                b"png", 16, 16)

    def make_style(self, img):
        rule = mapnik.Rule()
        rule.min_scale = 0
        rule.max_scale = 1000000000.0
        symbol = mapnik.PointSymbolizer(*img)
        symbol.allow_overlap = True
        rule.symbols.append(symbol)

        style = mapnik.Style()
        style.rules.append(rule)
        return style

    def mapnik_query(self, color):
        request_type = self.changerequest.request_type

        if request_type == models.Request.REQUEST_TYPE_NEW_LOCATION:
            # New one in green, old one in red
            if color == COLOR_NEW:
                return self.mapnik_query_the_geom()
            if color == COLOR_OLD:
                return self.mapnik_query_old_location()
        if request_type == models.Request.REQUEST_TYPE_REMOVE_CODE:
            # Only show the current one in red
            if color == COLOR_OLD:
                return self.mapnik_query_location()
        if request_type == models.Request.REQUEST_TYPE_MOVE_LOCATION:
            # New location in green, old location in red
            if color == COLOR_NEW:
                return self.mapnik_query_the_geom()
            if color == COLOR_OLD:
                return self.mapnik_query_location()

    def mapnik_query_the_geom(self):
        # This is an _awful_ way of doing it, I know. I lack time. To
        # work around a bug in Mapnik, there need to be little points
        # around the point, and I have no time to switch from postgis
        # to point symbolizers entirely.

        models.Points.points_around(
            self.changerequest.location_code + "_the_geom",
            self.changerequest.the_geom)

        return ("""(
            SELECT
                points.the_geom
            FROM
                changerequests_points AS points
            WHERE
                location_code = '%s_the_geom') data"""
                % (self.changerequest.location_code,))

    def mapnik_query_location(self):
        location = self.changerequest.get_location()

        if not location:
            return None

        models.Points.points_around(
            self.changerequest.location_code,
            location.the_geom)

        q = ("""(
            SELECT
                the_geom
            FROM
                changerequests_points
            WHERE
                changerequests_points.location_code = '%s') data""" %
                (self.changerequest.location_code,))
        return q

    def mapnik_query_old_location(self):
        if not self.changerequest.old_location_code:
            return None

        location = self.changerequest.get_location(
            location=self.changerequest.old_location_code)

        models.Points.points_around(
            self.changerequest.old_location_code,
            location.the_geom)

        q = ("""(
            SELECT
                the_geom
            FROM
                changerequests_points
            WHERE
                changerequests_points.location_code = '%s') data""" %
                (self.changerequest.old_location_code,))
        return q

    def layer(self, layer_ids=None, request=None):
        """Return mapnik layers and styles for a specific measurement
        type."""
        layers = []
        styles = {}

        if not self.changerequest:
            return

        for color in (COLOR_NEW, COLOR_OLD):
            query = self.mapnik_query(color)
            if query:
                img_file = "ball_{}.png".format(color)
                img = self.symbol_img(img_file)
                layer_desc = self.layer_desc(color)
                styles[layer_desc] = self.make_style(img)

                layer = mapnik.Layer(layer_desc, RD)
                layer.datasource = mapnik_datasource(query)
                layer.styles.append(layer_desc)
                layers.append(layer)

        logger.debug("layers, styles {} {}".format(layers, styles))
        return layers, styles

    def search(self, x, y, radius=10):
        if not self.changerequest:
            return

        rd_x, rd_y = google_to_rd(x, y)

        logger.debug("rdx, rdy: {} {}".format(rd_x, rd_y))

        my_x, my_y = (
            self.changerequest.the_geom.x,
            self.changerequest.the_geom.y)

        distance = math.sqrt((rd_x - my_x) ** 2 + (rd_y - my_y) ** 2)

        logger.debug("distance: {}".format(distance))

        if distance < radius:
            return [{
                    'name': unicode(self.changerequest),
                    'distance': distance,
                    'workspace_item': self.workspace_item,
                    'identifier': {
                        'changerequest_id': self.changerequest_id,
                        },
                    }]
        else:
            return []

    def location(self, changerequest_id, layout=None):
        """
        Who knows what a location function has to return?
        Hacked something together based on what fewsjdbc does.
        """
        if not self.changerequest:
            return

        return {
            "name": unicode(self.changerequest),
            "identifier": {
                'changerequest_id': self.changerequest_id,
                },
            "workspace_item": self.workspace_item,
            }

    def html(self, identifiers=None, layout_options=None):
        """
        """
        if not self.changerequest:
            return

        profile = pmodels.UserProfile.get_by_user(
            layout_options['request'].user)

        user_is_manager = profile.is_manager_in(
            self.changerequest.project)
        user_is_contractor = (
            profile.organization == self.changerequest.contractor.organization)

        context = RequestContext(
            layout_options['request'], {
                'cr': self.changerequest,
                'user_is_manager': user_is_manager,
                'user_is_contractor': user_is_contractor
                })

        return render_to_string(
            'changerequests/detail_popup.html',
            context_instance=context)

    def extent(self, identifiers=None):
        """
        Returns extent {'west':.., 'south':.., 'east':.., 'north':..}
        in google projection. None for each key means unknown.
        """
        if not self.changerequest:
            return {'west': None, 'south': None, 'east': None, 'north': None}

        cr = self.changerequest  # Purely to make it shorter to type

        west = east = cr.the_geom.x
        north = south = cr.the_geom.y

        if cr.old_location_code:
            try:
                old_location = pmodels.Location.objects.get(
                    project=cr.contractor.project,
                    location_code=cr.old_location_code)
                west = min(west, old_location.the_geom.x)
                east = max(east, old_location.the_geom.x)
                north = max(north, old_location.the_geom.y)
                south = min(south, old_location.the_geom.y)
            except pmodels.Location.DoesNotExist:
                pass

        gwest, gnorth = rd_to_google(west, north)
        geast, gsouth = rd_to_google(east, south)

        return {'west': gwest, 'south': gsouth,
                'east': geast, 'north': gnorth}
