# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

"""Helper functions to do with geography."""

# Python 3 is coming
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from lizard_map import coordinates


def rd_to_google_extent(rd_extent, extra_border=0.1):
    """Translate an extent that is in (minx, miny, maxx, maxy) RD
    projection format to a dictionary {'top': ... 'left': 'right':
    'bottom': } in Google projection.

    To make OpenLayers zoom better, the extent can get an
    extra_border. If this argument is 0.1, 10% of the width and
    breadth is added on all sides (so it's a 20% total increase per
    side).

    """

    topleft = rd_extent[0:2]
    bottomright = rd_extent[2:4]

    google_topleft = coordinates.rd_to_google(*topleft)
    google_bottomright = coordinates.rd_to_google(*bottomright)

    # To make sure we zoom in "correctly", with everything in view,
    # we now increase this extent some arbitrary percentage...
    dx = extra_border * abs(google_topleft[0] - google_bottomright[0])
    dy = extra_border * abs(google_topleft[1] - google_bottomright[1])

    # Format as a top/left/right/bottom dict with extra border
    extent = {
        'top': google_topleft[1] - dy,
        'left': google_topleft[0] - dx,
        'right': google_bottomright[0] + dx,
        'bottom': google_bottomright[1] + dy
    }

    return extent
