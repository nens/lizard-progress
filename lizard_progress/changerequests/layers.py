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
from lizard_map.workspace import WorkspaceItemAdapter

from lizard_progress.layers import mapnik_datasource
from lizard_progress import models as pmodels

from . import models

logger = logging.getLogger(__name__)


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

    def layer_desc(self, color="green"):
        desc = unicode(self.changerequest)
        if color == 'red':
            return b"Oude of te verwijderen locatie"
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
            if color == 'green':
                return self.mapnik_query_the_geom()
            if color == 'red':
                return self.mapnik_query_old_location()
        if request_type == models.Request.REQUEST_TYPE_REMOVE_CODE:
            # Only show the current one in red
            if color == 'red':
                return self.mapnik_query_location()
        if request_type == models.Request.REQUEST_TYPE_MOVE_LOCATION:
            # New location in green, old location in red
            if color == 'green':
                return self.mapnik_query_the_geom()
            if color == 'red':
                return self.mapnik_query_location()

    def mapnik_query_the_geom(self):
        return ("""(
            SELECT
                changerequest.the_geom
            FROM
                changerequests_request AS changerequest
            WHERE
                changerequest.id = %d) data""" %
                self.changerequest.id)

    def mapnik_query_location(self):
        q = ("""(
            SELECT
                lizard_progress_location.the_geom
            FROM
                lizard_progress_location
            WHERE
                lizard_progress_location.location_code = '%s'
            AND lizard_progress_location.project_id = %d) data""" %
                (self.changerequest.location_code,
                 self.changerequest.contractor.project_id))
        return q

    def mapnik_query_old_location(self):
        if not self.changerequest.old_location_code:
            return None

        q = ("""(
            SELECT
                lizard_progress_location.the_geom
            FROM
                lizard_progress_location
            WHERE
                lizard_progress_location.location_code = '%s'
            AND lizard_progress_location.project_id = %d) data""" %
                (self.changerequest.old_location_code,
                 self.changerequest.contractor.project_id))
        return q

    def layer(self, layer_ids=None, request=None):
        """Return mapnik layers and styles for a specific measurement
        type."""
        layers = []
        styles = {}

        if not self.changerequest:
            return

        for color in ('green', 'red'):
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
