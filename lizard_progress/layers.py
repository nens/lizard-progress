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

# Number of days to look back for computing the number of times
# a location has been inspected recently, to show on the map
RECENTLY_INSPECTED_DAYS = 14


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


def build_location_query(
        activity_id, is_point=None, complete=None, not_part_of_project=None,
        dates_matter=False, planned=None, ontime=None, numbers=False,
        work_impossible=False, new=False):
    """

    Args:
        work_impossible: if set to False or True locations marked as
            work_impossible will be excluded or included in the SQL query. If
            set to None it will not be taken into account in the query.
            The default is False because we don't want to take these locations
            into account in all our other queries.
    """
    if is_point and numbers:
        q = """(SELECT
                    loc.the_geom AS the_geom,
                    CASE WHEN COUNT(measurement) > 1
                        THEN to_char(COUNT(measurement), '999')
                        ELSE ''
                    END AS count
                FROM
                    lizard_progress_location loc
                LEFT OUTER JOIN
                    lizard_progress_measurement measurement
                ON
                    measurement.location_id = loc.id AND
                    measurement.parent_id IS NULL AND
                    measurement.date >= current_date - interval '{recent} days'
                WHERE
                    loc.activity_id = {activity_id} AND
                    {is_point_clause}
                    {complete_clause}
                    {not_part_of_project_clause}
                    {date_clause}
                    {work_impossible_clause}
                    {new_clause}
                    loc.the_geom IS NOT NULL
                GROUP BY
                    loc.the_geom
               ) data"""
    else:
        q = """(SELECT
                    loc.the_geom AS the_geom,
                    '' AS count
                FROM
                    lizard_progress_location loc
                WHERE
                    loc.activity_id = {activity_id} AND
                    {is_point_clause}
                    {complete_clause}
                    {not_part_of_project_clause}
                    {date_clause}
                    {work_impossible_clause}
                    {new_clause}
                    loc.the_geom IS NOT NULL
                GROUP BY
                    loc.the_geom
               ) data"""

    if is_point is None:
        is_point_clause = ""
    else:
        is_point_clause = "loc.is_point = {} AND".format(
            'true' if is_point else 'false')

    if complete is None:
        complete_clause = ""
    else:
        complete_clause = "loc.complete = {} AND".format(
            'true' if complete else 'false')

    if not_part_of_project is None:
        not_part_of_project_clause = ""
    else:
        not_part_of_project_clause = "loc.not_part_of_project = {} AND".format(
            'true' if not_part_of_project else 'false')

    if work_impossible is None:
        work_impossible_clause = ""
    else:
        work_impossible_clause = "loc.work_impossible = {} AND".format(
            'true' if work_impossible else 'false')

    if new is None:
        new_clause = ""
    else:
        new_clause = "loc.new = {} AND".format(
            'true' if new else 'false')

    if not dates_matter or complete:
        date_clause = ''
    else:
        if planned:
            if ontime:
                date_clause = ("loc.planned_date IS NOT NULL AND "
                               "loc.planned_date >= now()::date AND")
            else:
                date_clause = ("loc.planned_date IS NOT NULL AND "
                               "loc.planned_date < now()::date AND")
        else:
            date_clause = "loc.planned_date IS NULL AND "

    return q.format(
        recent=RECENTLY_INSPECTED_DAYS,
        activity_id=activity_id,
        is_point_clause=is_point_clause,
        complete_clause=complete_clause,
        not_part_of_project_clause=not_part_of_project_clause,
        date_clause=date_clause,
        work_impossible_clause=work_impossible_clause,
        new_clause=new_clause)


def make_point_style(img):
    def make_rule(min, max, img, overlap):
        rule = mapnik.Rule()
        rule.min_scale = min
        rule.max_scale = max

        filename, extension, x, y = img
        symbol = mapnik.ShieldSymbolizer(
            mapnik.Expression('[count]'), 'DejaVu Sans Book', 14,
            mapnik.Color("#000000"), mapnik.PathExpression(filename))
        symbol.allow_overlap = overlap
        rule.symbols.append(symbol)
        return rule

    cutoff = 5000

    # Below cutoff - allow overlap True
    rule_detailed = make_rule(0, cutoff, img, True)

    # Over cutoff - overlap False
    rule_global = make_rule(cutoff, 1000000000.0, img, False)

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
            self.activity = (
                models.Activity.objects.select_related().
                select_related('project__project_type').get(
                    pk=self.activity_id))

        except models.Activity.DoesNotExist:
            logger.debug("ACTIVITY {} DOES NOT EXIST".format(self.activity_id))
            self.activity = None
            return

        super(ProgressAdapter, self).__init__(*args, **kwargs)

    @property
    def show_numbers_on_map(self):
        return self.activity.show_numbers_on_map

    def mapnik_query_no_date(self, is_point, complete):
        return build_location_query(
            self.activity_id, is_point=is_point, complete=complete,
            not_part_of_project=False, numbers=self.show_numbers_on_map)

    def mapnik_query_locations_not_in_project(self):
        return build_location_query(
            self.activity_id, is_point=True, not_part_of_project=True,
            numbers=self.show_numbers_on_map)

    def mapnik_query_locations_work_impossible(self):
        return build_location_query(
            self.activity_id, is_point=True, work_impossible=True,
            numbers=self.show_numbers_on_map)

    def mapnik_query_locations_new(self):
        return build_location_query(
            self.activity_id, is_point=True, new=True,
            numbers=self.show_numbers_on_map)

    def mapnik_query_date(self, is_point, planned, ontime, complete):
        return build_location_query(
            self.activity_id, is_point=is_point, complete=complete,
            not_part_of_project=False,
            dates_matter=True, planned=planned, ontime=ontime,
            numbers=self.show_numbers_on_map)

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

        if self.show_numbers_on_map:
            # Show an extra layer with numbers for line locations that
            # have been uploaded frequently in the last weeks. The
            # same information for points is shown using shieldsymbolizers.
            self.add_layer_for_frequently_uploaded_locations(layers, styles)

        # Show an extra layer for point locations that are not
        # part of the project
        self.add_layer_for_locations_not_in_project(layers, styles)

        # Points that are impossible.
        self.add_layer_for_locations_work_impossible(layers, styles)

        # Unplanned locations that were found by the contractor.
        self.add_layer_for_locations_new(layers, styles)

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

    def add_layer_for_locations_work_impossible(self, layers, styles):
        layer_desc = '{} work impossible'.format(self.activity_id)
        layer = mapnik.Layer(layer_desc, RD)
        styles[layer_desc] = make_point_style(
            self.symbol_img("ball_work_impossible.png"))
        layer.datasource = mapnik_datasource(
            self.mapnik_query_locations_work_impossible())
        layer.styles.append(layer_desc)
        layers.append(layer)

    def add_layer_for_locations_new(self, layers, styles):
        layer_desc = '{} new'.format(self.activity_id)
        layer = mapnik.Layer(layer_desc, RD)
        styles[layer_desc] = make_point_style(
            self.symbol_img("ball_new.png"))
        layer.datasource = mapnik_datasource(
            self.mapnik_query_locations_new())
        layer.styles.append(layer_desc)
        layers.append(layer)

    def add_layer_for_frequently_uploaded_locations(self, layers, styles):
        """In some activities, if several separate (non-attachment)
        measurements for the same location were uploaded recently,
        show a number on the map indicating the number of
        measurements. This way locations that have to fixed /
        inspected often can be found.

        """
        layer_desc = 'Frequently uploaded locations for {}'.format(
            self.activity.id)
        layer = mapnik.Layer(layer_desc, RD)
        style = mapnik.Style()
        rule = mapnik.Rule()
        rule.symbols.append(mapnik.TextSymbolizer(
            mapnik.Expression("[count]"),
            'DejaVu Sans Book', 14, mapnik.Color('black')))
        style.rules.append(rule)
        styles[layer_desc] = style

        layer.datasource = mapnik_datasource("""
           (SELECT
                loc.the_geom AS the_geom,
                COUNT(m) AS count
            FROM
                lizard_progress_location loc
            LEFT OUTER JOIN
                lizard_progress_measurement m
            ON
                m.location_id = loc.id AND
                m.parent_id IS NULL AND
                m.date >= current_date - interval '{recent} days'
            WHERE
                loc.activity_id = {activity_id} AND
                loc.the_geom IS NOT NULL AND
                NOT loc.is_point
            GROUP BY
                loc.the_geom
            HAVING
                COUNT(m) > 1
            ) data""".format(activity_id=self.activity.id,
                             recent=RECENTLY_INSPECTED_DAYS))
        layer.styles.append(layer_desc)
        # Insert in front
        layers[0:0] = [layer]

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

        locations = list(
            Location.objects.filter(
                activity=self.activity,
                the_geom__distance_lte=(pt, D(m=distance))).
            distance(pt).order_by('distance'))

        logger.debug(">>>>>> maxdistance: {}".format(distance))
        for location in locations:
            logger.debug("{} {}".format(location, location.distance.m))
        location = None

        closest_point = (None, None)
        for location in locations:
            if location.is_point:
                closest_point = (location.distance.m, location)
                break

        closest_line = (None, None)
        for location in locations:
            if not location.is_point:
                closest_line = (location.distance.m, location)
                break

        if closest_point[1] is None:
            logger.debug("Closest point is None, pick closest line")
            location = closest_line[1]
        elif closest_line[1] is None:
            logger.debug("Closest line is None, pick closest point")
            location = closest_point[1]
        else:
            logger.debug("Both not None, pick the closest")
            # BUT give the put a 10%+50cm bonus to make it possible to click it
            both = [closest_line,
                    (closest_point[0] * 0.9 - 0.5, closest_point[1])]
            logger.debug(unicode(both))
            both.sort()
            location = both[0][1]
            logger.debug("Picked {}".format(location))

        if location is not None:
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
        else:
            results = []
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

        if not location.measurement_set.exists():
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
