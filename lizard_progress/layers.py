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

from lizard_progress.models import Contractor
from lizard_progress.models import Hydrovak
from lizard_progress.models import Location
from lizard_progress.models import MeasurementType
from lizard_progress.models import Project
from lizard_progress.models import ScheduledMeasurement

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


class ProgressAdapter(WorkspaceItemAdapter):  # pylint: disable=W0223
    def __init__(self, *args, **kwargs):
        if ('layer_arguments' not in kwargs or
            not isinstance(kwargs['layer_arguments'], dict)):
            raise ValueError(
                'Argument layer_arguments of adapter should be a dict.')

        project_slug = kwargs['layer_arguments'].get('project_slug', None)
        contractor_slug = (kwargs['layer_arguments'].
                           get('contractor_slug', None))
        measurement_type_slug = (kwargs['layer_arguments'].
                                 get('measurement_type_slug', None))

        self.project = None
        self.contractor = None
        self.measurement_type = None

        try:
            self.project = Project.objects.get(slug=project_slug)
        except Project.DoesNotExist:
            return

        try:
            self.contractor = Contractor.objects.get(project=self.project,
                                                     slug=contractor_slug)
        except Contractor.DoesNotExist:
            return

        try:
            self.measurement_type = (MeasurementType.objects.
                                     get(project=self.project,
                                         mtype__slug=measurement_type_slug))
        except MeasurementType.DoesNotExist:
            pass  # Show for all measurement types

        super(ProgressAdapter, self).__init__(*args, **kwargs)

    @staticmethod
    def make_style(img):
        def make_rule(min, max, img, overlap):
            rule = mapnik.Rule()
            rule.min_scale = min
            rule.max_scale = max
            symbol = mapnik.PointSymbolizer(*img)
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

    def mapnik_query(self, complete):
        if self.measurement_type is None:
            # If there is no measurement_type, we combine them all and
            # show different icons in case there are no measurements
            # complete (or is false and and is false), they are all
            # complete (or is true and and is true) and also if only
            # some of them are complete (or is true and and is false).
            q = """(SELECT
                        loc.the_geom
                    FROM
                        lizard_progress_location loc
                    INNER JOIN
                         lizard_progress_scheduledmeasurement sm
                    ON
                         sm.location_id = loc.id
                    WHERE
                         sm.contractor_id=%d AND
                         sm.project_id=%d AND
                         loc.the_geom IS NOT NULL
                    GROUP BY
                         loc.the_geom
                    HAVING bool_or(sm.complete)=%s AND
                           bool_and(sm.complete)=%s
                   ) data"""
            if complete == True:
                return q % (self.contractor.id, self.project.id,
                            "true", "true")
            elif complete == False:
                return q % (self.contractor.id, self.project.id,
                            "false", "false")
            elif complete == "some":
                return q % (self.contractor.id, self.project.id,
                            "true", "false")

        else:
            return ("""(
                  SELECT
                      loc.the_geom
                  FROM
                      lizard_progress_location loc
                  INNER JOIN
                      lizard_progress_scheduledmeasurement sm
                  ON
                      sm.location_id = loc.id
                  WHERE
                      sm.complete=%s
                  AND sm.contractor_id=%d
                  AND sm.project_id=%d
                  AND sm.measurement_type_id=%d
                  AND loc.the_geom IS NOT NULL) data""" %
                    (str(complete).lower(),
                     self.contractor.id,
                     self.project.id,
                     self.measurement_type.id))

    def layer_desc(self, complete):
        mtname = self.measurement_type.name if self.measurement_type else "all"
        return str(" ".join([
                    self.project.slug,
                    self.contractor.slug,
                    mtname,
                    str(complete)]))

    def layer_all_types(self, layer_ids=None, request=None):
        "Return mapnik layers and styles for all measurement types."
        layers = []
        styles = {}

        for complete in (True, False, "some"):
            layer_desc = self.layer_desc(complete)
            if complete == True:
                img = self.symbol_img("ball_green.png")
            elif complete == False:
                img = self.symbol_img("ball_red.png")
            else:
                img = self.symbol_img("ball_yellow.png")

            styles[layer_desc] = self.make_style(img)

            layer = mapnik.Layer(layer_desc, RD)
            layer.datasource = mapnik_datasource(
                self.mapnik_query(complete))
            layer.styles.append(layer_desc)
            layers.append(layer)

        return layers, styles

    def layer(self, layer_ids=None, request=None):
        """Return mapnik layers and styles for a specific measurement
        type."""
        layers = []
        styles = {}

        if not self.project or not self.contractor:
            return

        if not self.measurement_type:
            return self.layer_all_types(layer_ids, request)

        for complete in (True, False):
            layer_desc = self.layer_desc(complete)

            if complete:
                img_file = str(self.measurement_type.icon_complete)
            else:
                img_file = str(self.measurement_type.icon_missing)
            if not img_file:
                img_file = "ball_%s.png" % ("green" if complete else "red",)

            img = self.symbol_img(img_file)
            styles[layer_desc] = self.make_style(img)

            layer = mapnik.Layer(layer_desc, RD)
            layer.datasource = mapnik_datasource(
                self.mapnik_query(complete))
            layer.styles.append(layer_desc)
            layers.append(layer)

        return layers, styles

    def search(self, x, y, radius=None):
        """
        """

        pt = Point(coordinates.google_to_rd(x, y), 4326)

        # Looking at how radius is derived in lizard_map.js, it's best applied
        # to the y-coordinate to get a reasonable search distance in meters.

        lon1, lat1 = coordinates.google_to_wgs84(x, y - radius)
        lon2, lat2 = coordinates.google_to_wgs84(x, y + radius)

        # On my computer, a call to Proj() is needed

        pyproj.Proj(init='epsg:4326')

        # before Geod

        geod = pyproj.Geod(ellps='WGS84')

        # Django chrashes with:

        # Rel. 4.7.1, 23 September 2009
        # <(null)>:
        # ellipse setup failure
        # program abnormally terminated

        _forward, _backward, distance = geod.inv(lon1, lat1, lon2, lat2)
        distance /= 2.0

        # Find all profiles within the search distance. Order them by distance.

        results = []

        for location in (Location.objects.
                         filter(project=self.project,
                                the_geom__distance_lte=(pt, D(m=distance))).
                         distance(pt).order_by('distance')):
            if self.measurement_type:
                scheduleds = (ScheduledMeasurement.objects.
                              filter(location=location,
                                     contractor=self.contractor,
                                     measurement_type=self.measurement_type))
            else:
                scheduleds = (ScheduledMeasurement.objects.
                              filter(location=location,
                                     contractor=self.contractor,
                               measurement_type__mtype__can_be_displayed=True).
                              order_by('measurement_type__mtype__name'))

            for scheduled in scheduleds:
                result = {
                    'name': '%s %s %s' % (location.location_code,
                                          scheduled.measurement_type.name,
                                          self.contractor.name),
                    'distance': location.distance.m,
                    'workspace_item': self.workspace_item,
                    'identifier': {
                        'scheduled_measurement_id': scheduled.id,
                        },
                    'grouping_hint': 'lizard_progress %s %s %s %s' % (
                        self.workspace_item.id,
                        self.contractor.slug,
                        self.project.slug,
                        scheduled.measurement_type.slug),
                    }
                results.append(result)
            if results:
                # For now, only show info from one location because
                # our templates don't really work with more yet
                break

        logger.debug("Results=" + str(results))
        return results

    def location(self, scheduled_measurement_id, layout=None):
        """
        Who knows what a location function has to return?
        Hacked something together based on what fewsjdbc does.
        """
        try:
            scheduled = (ScheduledMeasurement.objects.
                         get(pk=scheduled_measurement_id))
        except ScheduledMeasurement.DoesNotExist:
            return None

        grouping_hint = "lizard_progress::%s::%s::%s" % (
            scheduled.project.slug,
            scheduled.contractor.slug,
            scheduled.measurement_type.slug)

        return {
            "name": "%s %s %s" %
            (scheduled.location.location_code,
             scheduled.measurement_type.name,
             scheduled.contractor.name,),
            "identifier": {
                "location": scheduled_measurement_id,
                "grouping_hint": grouping_hint,
                },
            "workspace_item": self.workspace_item,
            "google_coords": (scheduled.location.the_geom.x,
                              scheduled.location.the_geom.y),
            }

    def symbol_url(self):
        ""
        img_file = "ball_green.png"
        if self.measurement_type:
            if self.measurement_type.icon_complete:
                img_file = str(self.measurement_type.icon_complete)

        return settings.STATIC_URL + 'lizard_progress/' + img_file

    def symbol_img(self, img_file):
        return (resource_filename("lizard_progress",
                                  ("/static/lizard_progress/%s" % img_file)),
                "png", 16, 16)

    def html(self, identifiers=None, layout_options=None):
        """
        """
        scheduled_measurements = [ScheduledMeasurement.objects.
                                  get(pk=id['scheduled_measurement_id'])
                                  for id in identifiers]

        if not scheduled_measurements:
            return

        sm = scheduled_measurements[0]

        if not sm.complete:
            return super(ProgressAdapter, self).html_default(
                identifiers=identifiers,
                layout_options=layout_options,
                template='lizard_progress/incomplete_measurement.html',
                extra_render_kwargs={
                    'scheduled_measurements': scheduled_measurements})

        else:
            handler = (self.project.specifics().
                       html_handler(measurement_type=sm.measurement_type,
                                    contractor=sm.contractor))

        if handler is not None:
            return handler(super(ProgressAdapter, self).html_default,
                           scheduled_measurements,
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
        if not self.project or not self.contractor:
            return {'west': None, 'south': None, 'east': None, 'north': None}

        locations = Location.objects.filter(
            project=self.project,
            scheduledmeasurement__contractor=self.contractor)

        if self.measurement_type:
            locations = locations.filter(
                scheduledmeasurement__measurement_type=self.measurement_type)

        if not locations.exists():
            return {'west': None, 'south': None, 'east': None, 'north': None}

        west, south, east, north = locations.only("the_geom").extent()
        west, south = rd_to_google(west, south)
        east, north = rd_to_google(east, north)
        return {'west': west, 'south': south, 'east': east, 'north': north}

    def image(self, identifiers=None, start_date=None, end_date=None,
              width=None, height=None, layout_extra=None):

        scheduled_measurements = [ScheduledMeasurement.objects.
                                  get(pk=id['scheduled_measurement_id'])
                                  for id in identifiers]

        if not scheduled_measurements:
            return

        sm = scheduled_measurements[0]
        handler = (self.project.specifics().
                   image_handler(measurement_type=sm.measurement_type,
                                 contractor=sm.contractor))

        if handler is not None:
            return handler(scheduled_measurements)


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
