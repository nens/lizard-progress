# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

"""Helper functions to do with geography."""

# Python 3 is coming
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from django.contrib.gis.geos import LineString
from django.contrib.gis.geos import Point

from osgeo import ogr

from lizard_progress.util import coordinates


def rd_to_wgs84_extent(rd_extent, extra_border=0.1):
    """Translate an extent that is in (minx, miny, maxx, maxy) RD
    projection format to a dictionary {'top': ... 'left': 'right':
    'bottom': } in Google projection.
    To make OpenLayers zoom better, the extent can get an
    extra_border. If this argument is 0.1, 10% of the width and
    breadth is added on all sides (so it's a 20% total increase per
    side).
    """
    _topleft = rd_extent[0:2]
    _bottomright = rd_extent[2:4]

    topleft = coordinates.rd_to_wgs84(*_topleft)
    bottomright = coordinates.rd_to_wgs84(*_bottomright)

    # To make sure we zoom in "correctly", with everything in view,
    # we now increase this extent some arbitrary percentage...
    dx = extra_border * abs(topleft[0] - bottomright[0])
    dy = extra_border * abs(topleft[1] - bottomright[1])

    # Format as a top/left/right/bottom dict with extra border
    return {
        'top': topleft[1] - dy,
        'left': topleft[0] - dx,
        'right': bottomright[0] + dx,
        'bottom': bottomright[1] + dy
    }


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


def is_line(geom):
    """Decide whether geom is a line geometry (of several possible types)."""
    if isinstance(geom, LineString):
        # django.contrib.gis.geos.LineString
        return True

    if hasattr(geom, 'ExportToWkt') and 'LINESTRING' in geom.ExportToWkt():
        # osgeo.ogr.Geometry linestring
        return True

    if isinstance(geom, basestring) and 'LINESTRING' in geom:
        # A WKT string
        return True

    return False


def get_midpoint(line):
    """Takes a ogr linestring and returns the point between its first and
    last points."""
    points = line.GetPoints()
    first = points[0]
    last = points[-1]

    x = (first[0] + last[0]) / 2
    y = (first[1] + last[1]) / 2

    return ogr.CreateGeometryFromWkt('POINT ({} {})'.format(x, y))


def osgeo_3d_line_to_2d_wkt(geom):
    points = geom.GetPoints()
    return 'LINESTRING({} {}, {} {})'.format(
        points[0][0], points[0][1],
        points[1][0], points[1][1])


def osgeo_3d_point_to_2d_wkt(geom):
    if isinstance(geom, Point):
        # Geos point, not osgeo
        x, y = geom.x, geom.y
    else:
        point = geom.GetPoint()
        x, y = point[:2]

    return 'POINT({} {})'.format(x, y)
