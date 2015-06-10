# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.txt.

from django.conf import settings
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from lizard_map import coordinates
from lizard_map.coordinates import RD
from lizard_map.coordinates import rd_to_google
from lizard_map.workspace import WorkspaceItemAdapter

from pkg_resources import resource_filename  # pylint: disable=E0611
import logging
import mapnik
import pyproj

from lizard_progress import models
from lizard_progress.models import Hydrovak
from lizard_progress.models import Location

logger = logging.getLogger(__name__)


def mapnik_datasource(query):
    default_database = settings.DATABASES['default']
    return mapnik.PostGIS(
        host=default_database['HOST'],
        port=default_database['PORT'],
        user=default_database['USER'],
        password=default_database['PASSWORD'],
        dbname=default_database['NAME'],
        table=query.encode('utf8')
        )


def make_point_style(img):
    def make_rule(min, max, img, overlap):
        rule = mapnik.Rule()
        rule.min_scale = min
        rule.max_scale = max

        filename, extension, x, y = img
        symbol = mapnik.PointSymbolizer()
        symbol.filename = filename
        symbol.allow_overlap = overlap
        rule.symbols.append(symbol)
        return rule

    # Below cutoff - allow overlap True
    rule_detailed = make_rule(0, 50000, img, True)

    # Over cutoff - overlap False
    rule_global = make_rule(50000, 1000000000.0, img, False)

    style = mapnik.Style()
    style.rules.append(rule_detailed)
    style.rules.append(rule_global)
    return style


def make_line_style(color):
    def make_rule(color):
        rule = mapnik.Rule()
        symbol = mapnik.LineSymbolizer(mapnik.Color(color), 2.5)
        rule.symbols.append(symbol)
        return rule

    style = mapnik.Style()
    style.rules.append(make_rule(color))
    return style


class ProgressAdapter(WorkspaceItemAdapter):  # pylint: disable=W0223
    def __init__(self, *args, **kwargs):
        logger.debug("{} {}".format(args, kwargs))
        if ('layer_arguments' not in kwargs or
                not isinstance(kwargs['layer_arguments'], dict)):
            raise ValueError(
                'Argument layer_arguments of adapter should be a dict.')

        self.activity_id = kwargs['layer_arguments'].get('activity_id', None)

        try:
            self.activity = models.Activity.objects.get(
                pk=self.activity_id)
        except models.Activity.DoesNotExist:
            logger.debug("ACTIVITY {} DOES NOT EXIST".format(self.activity_id))
            self.activity = None
            return

        super(ProgressAdapter, self).__init__(*args, **kwargs)

    def mapnik_query_no_date(self, is_point, complete):
        q = """(SELECT
                    loc.the_geom
                 FROM
                    lizard_progress_location loc
                WHERE
                    loc.activity_id = %d AND
                    loc.the_geom IS NOT NULL AND
                    loc.is_point = %s AND
                    loc.complete = %s AND
                    loc.not_part_of_project = false
                ) data"""

        return q % (
            self.activity_id, "true" if is_point else "false",
            "true" if complete else "false",
        )

    def mapnik_query_locations_not_in_project(self):
        q = """(SELECT
                   loc.the_geom
                FROM
                   lizard_progress_location loc
                WHERE
                   loc.activity_id = {} AND
                   loc.the_geom IS NOT NULL AND
                   loc.is_point = true AND
                   loc.not_part_of_project = true
               ) data"""

        return q.format(self.activity_id)

    def mapnik_query_date(self, is_point, planned, ontime, complete):
        q = """(SELECT
                    loc.the_geom
                 FROM
                    lizard_progress_location loc
                WHERE
                    loc.activity_id = %d AND
                    loc.the_geom IS NOT NULL AND
                    loc.is_point = %s AND
                    loc.complete = %s AND
                    loc.not_part_of_project = false AND
                    %s
                ) data"""

        if complete:
            date_query = "1 = 1"
        else:
            if planned:
                if ontime:
                    date_query = ("loc.planned_date IS NOT NULL AND "
                                  "loc.planned_date >= now()::date")
                else:
                    date_query = ("loc.planned_date IS NOT NULL AND "
                                  "loc.planned_date < now()::date")
            else:
                date_query = "loc.planned_date IS NULL"

        query = q % (self.activity_id, "true" if is_point else "false",
                     "true" if complete else "false",
                     date_query)
        logger.debug(query)
        return query

    def layer_desc(self, complete):
        return "{} {} {}".format(
            self.activity.project.slug, self.activity.id, complete)

    def layer_desc_date(self, is_point, complete, planned, ontime):
        return "{} {} {} {} {}".format(
            self.activity.id, is_point, complete, planned, ontime)

    def layer(self, layer_ids=None, request=None):
        if self.activity.specifics().allow_planning_dates:
            layers, styles = self.layer_date(layer_ids, request)
        else:
            layers, styles = self.layer_no_date(layer_ids, request)

        if self.locations_not_in_project_different:
            # Show an extra layer for point locations that are not
            # part of the project
            self.add_layer_for_locations_not_in_project(layers, styles)

        return layers, styles

    def layer_no_date(self, layer_ids=None, request=None):
        """Return mapnik layers and styles for all measurement types,
        don't care about planned dates."""
        layers = []
        styles = {}

        for is_point, complete in (
                (True, True), (True, False), (False, True), (False, False)):
            if is_point:
                layer_desc = self.layer_desc(complete)
                img = (self.symbol_img("ball_green.png") if complete
                       else self.symbol_img("ball_red.png"))
                styles[layer_desc] = make_point_style(img)
            else:
                # Line
                layer_desc = self.layer_desc(complete) + 'line'
                color = '#00FF00' if complete else '#FF0000'
                styles[layer_desc] = make_line_style(color)

            layer = mapnik.Layer(layer_desc, RD)
            layer.datasource = mapnik_datasource(
                self.mapnik_query_no_date(is_point, complete))
            layer.styles.append(layer_desc)
            layers.append(layer)

        return layers, styles

    def layer_date(self, layer_ids=None, request=None):
        """Return mapnik layers and styles for all measurement types,
        don't care about planned dates.

        Four colors:
        - complete: green
        - not complete, planned, on time: black
        - not complete, planned, late: yellow
        - not complete, not planned: red

        All those for both points and lines.
        """

        layers = []
        styles = {}

        for is_point, complete, planned, ontime, color, hexcolor in (
                (True, True, None, None, "green", "#00FF00"),
                (True, False, True, True, "black", "#000000"),
                (True, False, True, False, "yellow", "#ffff00"),
                (True, False, False, None, "red", "#ff0000"),
                (False, True, None, None, "green", "#00ff00"),
                (False, False, True, True, "black", "#000000"),
                (False, False, True, False, "orange", "#ffff00"),
                (False, False, False, None, "red", "#ff0000"),
        ):
            layer_desc = self.layer_desc_date(
                is_point, complete, planned, ontime)

            if is_point:
                img = self.symbol_img("ball_{}.png".format(color))
                styles[layer_desc] = make_point_style(img)
            else:
                # Line
                styles[layer_desc] = make_line_style(hexcolor)

            layer = mapnik.Layer(layer_desc, RD)
            layer.datasource = mapnik_datasource(
                self.mapnik_query_date(is_point, planned, ontime, complete))
            layer.styles.append(layer_desc)
            layers.append(layer)

        return layers, styles

    def add_layer_for_locations_not_in_project(self, layers, styles):
        layer_desc = '{} locations of other owners'.format(self.activity_id)
        layer = mapnik.Layer(layer_desc, RD)
        styles[layer_desc] = make_point_style(self.symbol_img("ball_grey.png"))
        layer.datasource = mapnik_datasource(
            self.mapnik_query_locations_not_in_project())
        layer.styles.append(layer_desc)
        layers.append(layer)

    def search(self, x, y, radius=None):
        """
        """

        pt = Point(coordinates.google_to_rd(x, y), 4326)

        # Looking at how radius is derived in lizard_map.js, it's best applied
        # to the y-coordinate to get a reasonable search distance in meters.

        lon1, lat1 = coordinates.google_to_wgs84(x, y - radius)
        lon2, lat2 = coordinates.google_to_wgs84(x, y + radius)

        pyproj.Proj(init='epsg:4326')
        geod = pyproj.Geod(ellps='WGS84')
        _forward, _backward, distance = geod.inv(lon1, lat1, lon2, lat2)
        distance /= 2.0

        # Find all profiles within the search distance. Order them by distance.

        results = []

        for location in (Location.objects.filter(
                activity=self.activity,
                the_geom__distance_lte=(pt, D(m=distance))).
                distance(pt).order_by('distance')):

            # If we found multiple locations, some of them may be
            # points and some of them may be line elements. We want to
            # return the first point if there are points, and the
            # first line otherwise.
            if not results or location.is_point:
                results = [{
                    'name': unicode(location),
                    'distance': location.distance.m,
                    'workspace_item': self.workspace_item,
                    'identifier': {
                        'location_id': location.id,
                    },
                    'grouping_hint': 'lizard_progress %s %s' % (
                        self.workspace_item.id,
                        self.activity.id)
                }]

            if location.is_point:
                break

        logger.debug("Results=" + str(results))
        return results

    def location(self, location_id, layout=None):
        """
        Who knows what a location function has to return?
        Hacked something together based on what fewsjdbc does.
        """
        try:
            location = Location.objects.get(pk=location_id)
        except Location.DoesNotExist:
            return None

        grouping_hint = "lizard_progress::%s" % (self.activity.id,)

        return {
            "name": "%s %s %s" %
            (location.location_code,
             self.activity.measurement_type.name,
             self.activity.contractor.name,),
            "identifier": {
                "location": location_id,
                "grouping_hint": grouping_hint,
                },
            "workspace_item": self.workspace_item,
            "google_coords": (location.the_geom.x,
                              location.the_geom.y),
            }

    def symbol_url(self):
        ""
        img_file = "ball_green.png"

        return settings.STATIC_URL + 'lizard_progress/' + img_file

    def symbol_img(self, img_file):
        return (resource_filename("lizard_progress",
                                  ("/static/lizard_progress/%s" % img_file)),
                "png", 16, 16)

    def html(self, identifiers=None, layout_options=None):
        """
        """
        locations = list(Location.objects.filter(
            activity_id=self.activity_id,
            pk__in=[identifier['location_id'] for identifier in identifiers]
        ))

        if not locations:
            return

        # Silly limitation: we only show info for the first of the found
        # locations. Zoom in further if you need more...
        location = locations[0]

        if not location.complete:
            return super(ProgressAdapter, self).html_default(
                identifiers=identifiers,
                layout_options=layout_options,
                template='lizard_progress/incomplete_measurement.html',
                extra_render_kwargs={
                    'activity': self.activity,
                    'location': location})

        else:
            handler = self.activity.specifics().html_handler()

        if handler is not None:
            return handler(super(ProgressAdapter, self).html_default,
                           locations,
                           identifiers=identifiers,
                           layout_options=layout_options)

        # Otherwise just use the default template (give implementing
        # sites the chance to just implement image)
        return super(ProgressAdapter, self).html_default(
            template='lizard_progress/html_default.html',
            identifiers=identifiers,
            layout_options=layout_options,
        )

    def extent(self, identifiers=None):
        """
        Returns extent {'west':.., 'south':.., 'east':.., 'north':..}
        in google projection. None for each key means unknown.
        """
        if not self.activity:
            return {'west': None, 'south': None, 'east': None, 'north': None}

        locations = Location.objects.filter(activity=self.activity)

        if not locations.exists():
            return {'west': None, 'south': None, 'east': None, 'north': None}

        west, south, east, north = locations.only("the_geom").extent()
        west, south = rd_to_google(west, south)
        east, north = rd_to_google(east, north)
        return {'west': west, 'south': south, 'east': east, 'north': north}

    def image(self, identifiers=None, start_date=None, end_date=None,
              width=None, height=None, layout_extra=None):

        locations = list(Location.objects.filter(
            pk__in=[identifier['location_id'] for identifier in identifiers]))

        if not locations:
            return

        handler = self.activity.specifics().image_handler()

        if handler is not None:
            return handler(locations)


class HydrovakAdapter(WorkspaceItemAdapter):
    """HydrovakAdapter."""

    def __init__(self, *args, **kwargs):
        self.project_slug = kwargs['layer_arguments'].get('project_slug', None)
        super(HydrovakAdapter, self).__init__(*args, **kwargs)

    def layer(self, layer_ids=None, request=None):
        layers = []
        styles = {}

        rule = mapnik.Rule()
        symbol = mapnik.LineSymbolizer(mapnik.Color("#0000FF"), 4.0)
        rule.symbols.append(symbol)
        style = mapnik.Style()
        style.rules.append(rule)

        hydrovakken = Hydrovak.objects.filter(
            project__slug="'%s'" % self.project_slug).only("the_geom")
        query = "(%s) data" % hydrovakken.query
        layer = mapnik.Layer('Hydrovakken', RD)
        layer.datasource = mapnik_datasource(query)
        layer.styles.append('hydrovak')

        layers.append(layer)
        styles['hydrovak'] = style

        return layers, styles

    def extent(self, identifiers=None):
        "Return extent in Google projection."
        west, south, east, north = Hydrovak.objects.filter(
            project__slug=self.project_slug).only("the_geom").extent()
        west, south = rd_to_google(west, south)
        east, north = rd_to_google(east, north)
        return {'west': west, 'south': south, 'east': east, 'north': north}

    def search(self, x, y, radius=None):
        return []
