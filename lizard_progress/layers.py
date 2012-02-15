# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.txt.

from django.conf import settings
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from lizard_map import coordinates
from lizard_map.coordinates import RD
from lizard_map.workspace import WorkspaceItemAdapter
from pkg_resources import resource_filename
import logging
import mapnik
import pyproj

from lizard_progress.models import Contractor
from lizard_progress.models import Location
from lizard_progress.models import MeasurementType
from lizard_progress.models import Project
from lizard_progress.models import ScheduledMeasurement

logger = logging.getLogger(__name__)


class ProgressAdapter(WorkspaceItemAdapter):
    def __init__(self, *args, **kwargs):
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
                                         slug=measurement_type_slug))
        except MeasurementType.DoesNotExist:
            return

        super(ProgressAdapter, self).__init__(*args, **kwargs)

    def layer(self, layer_ids=None, request=None):
        "Return mapnik layers and styles."
        layers = []
        styles = {}

        if not (self.project and self.contractor and self.measurement_type):
            return

        for complete in (True, False):
            layer_desc = str("%s %s %s %s" % (self.project.slug,
                                              self.contractor.slug,
                                              self.measurement_type.name,
                                              str(complete)))
            logger.debug(layer_desc)

            query = ("""(select loc.the_geom from lizard_progress_location loc
                  inner join lizard_progress_scheduledmeasurement sm on
                  sm.location_id = loc.unique_id
                  where sm.complete=%s
                  and sm.contractor_id=%d
                  and sm.project_id=%d
                  and sm.measurement_type_id=%d) data""" %
                     (str(complete).lower(),
                      self.contractor.id,
                      self.project.id,
                      self.measurement_type.id))

            default_img_file = "ball_%s.png" % ("green" if complete else "red",)
            img_file = str(self.measurement_type.icon_complete if complete
                        else self.measurement_type.icon_missing) or default_img_file

            img = (resource_filename("lizard_progress",
                                     ("/static/lizard_progress/%s" % img_file)),
                   "png", 16, 16)

            img_file_global = str(self.measurement_type.global_icon_complete if complete
                                  else "emptycircle16.png")
            img_global = (resource_filename("lizard_progress",
                                            "/static/lizard_progress/%s" % img_file_global),
                          "png", 16, 16)
            
            style = mapnik.Style()
            styles[layer_desc] = style

            rule_detailed = mapnik.Rule()
            rule_detailed.min_scale = 0
            rule_detailed.max_scale = 50000

            symbol = mapnik.PointSymbolizer(*img)
            symbol.allow_overlap = True
            rule_detailed.symbols.append(symbol)

            rule_global = mapnik.Rule()
            rule_global.min_scale = 50000
            rule_global.max_scale = 1000000000.0 # "inf"

            symbol_global = mapnik.PointSymbolizer(*img_global)
            symbol_global.allow_overlap = False
            rule_global.symbols.append(symbol_global)

            style.rules.append(rule_detailed)
            style.rules.append(rule_global)

            default_database = settings.DATABASES['default']
            datasource = mapnik.PostGIS(
                host=default_database['HOST'],
                port=default_database['PORT'],
                user=default_database['USER'],
                password=default_database['PASSWORD'],
                dbname=default_database['NAME'],
                table=query.encode('ascii')
                )

            layer = mapnik.Layer(layer_desc, RD)
            layer.datasource = datasource
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

        forward, backward, distance = geod.inv(lon1, lat1, lon2, lat2)
        distance /= 2.0

        # Find all profiles within the search distance. Order them by distance.

        results = []

        for location in (Location.objects.
                         filter(project=self.project,
                                the_geom__distance_lte=(pt, D(m=distance))).
                         distance(pt).order_by('distance')):
            for scheduled in (ScheduledMeasurement.objects.
                              filter(location=location,
                                     contractor=self.contractor,
                                     measurement_type=self.measurement_type,
                                     complete=True)):
                result = {
                    'name': '%s %s %s' % (location.unique_id, self.measurement_type.name,
                                          self.contractor.name),
                    'distance': location.distance.m,
                    'workspace_item': self.workspace_item,
                    'identifier': {
                        'scheduled_measurement_id': scheduled.id,
                        },
                    'grouping_hint': '%s %s' % (self.project.slug, self.measurement_type.slug),
                    }
                results.append(result)
                break
            if results:
                break

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

        return {"name": "%s %s %s" %
                (scheduled.location.unique_id,
                 scheduled.measurement_type.name,
                 scheduled.contractor.name,),
                "identifier": {
                "location": scheduled_measurement_id
                },
                "workspace_item": self.workspace_item,
                "google_coords": (scheduled.location.the_geom.x,
                                  scheduled.location.the_geom.y),
                }

    def symbol_url(self):
        ""
        default_img_file = "ball_green.png"
        img_file = str(self.measurement_type.icon_complete) or default_img_file

        return settings.STATIC_URL + 'lizard_progress/'+ img_file

    def html(self, identifiers=None, layout_options=None):
        """
        """
        scheduled_measurements = [ScheduledMeasurement.objects.
                                  get(pk=id['scheduled_measurement_id'])
                                  for id in identifiers]

        handler = (self.project.specifics().
                   html_handler(measurement_type=self.measurement_type,
                                contractor=self.contractor,
                                project=self.project))

        if handler is not None:
            return handler(super(ProgressAdapter, self).html_default,
                           scheduled_measurements,
                           identifiers=identifiers,
                           layout_options=layout_options)

        # Otherwise just use the default template (give implementing
        # sites the chance to just implement image)
        return super(ProgressAdapter, self).html_default(
            identifiers=identifiers,
            layout_options=layout_options,
        )

    def extent(self, identifiers=None):
        """
        Returns extent {'west':.., 'south':.., 'east':.., 'north':..}
        in google projection. None for each key means unknown.
        """

        print "EEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEE"
        print "EXTENT"

        return {
            'west': None, 'south': None,
            'east': None, 'north': None
        }

    def image(self, identifiers=None, start_date=None, end_date=None,
              width=None, height=None, layout_extra=None):

        scheduled_measurements = [ScheduledMeasurement.objects.
                                  get(pk=id['scheduled_measurement_id'])
                                  for id in identifiers]

        handler = (self.project.specifics().
                   image_handler(measurement_type=self.measurement_type,
                                 contractor=self.contractor,
                                 project=self.project))

        if handler is not None:
            return handler(scheduled_measurements)
