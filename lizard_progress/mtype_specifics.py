"""Each measurement type has specifics that define its behavior, like
how to show a measurement in a popup, or whether an uploaded file
should be treated as linelike or as binary.

This module defines a Specifics object for each measurement type.
"""

import logging

from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas

from django.http import HttpResponse

from metfilelib.util.linear_algebra import Line, Point

import lizard_progress.parsers.attachment_parser
import lizard_progress.parsers.lab_csv_parser
import lizard_progress.parsers.met_parser
import lizard_progress.parsers.oeverfoto_parser
import lizard_progress.parsers.oeverkenmerk_parser
import lizard_progress.parsers.peilschaal_csv_parser
import lizard_progress.parsers.peilschaal_jpg_parser
import lizard_progress.parsers.ribx_parser

from lizard_progress import models
from lizard_progress.views import ScreenFigure

logger = logging.getLogger(__name__)

FILE_IMAGE = object()
FILE_NORMAL = object()
FILE_READER = object()


class GenericSpecifics(object):
    """
    Example / base Specifics implementation.

    The goal of this class is threefold:
    - Have a specifics implementation we can use for testing
    - Have an implementation that can be used as a blueprint (you can
      inherit this class, if you wish).
    - To have a class with this name.
    """

    allow_planning_dates = False
    location_types = [models.Location.LOCATION_TYPE_POINT]

    def __init__(self, activity):
        self.activity = activity
        self.project = activity.project
        self.measurement_type = activity.measurement_type
        self.organization = activity.contractor

    # The below are named "sample_" so that the adapter can see that
    # the real html_handler and image_handler aren't implemented.  In
    # your own Specifics objects, they need to be named
    # 'html_handler' and 'image_handler'.

    def sample_html_handler(self, html_default, locations,
                            identifiers, layout_options):
        """A function that can generate popup HTML for this measurement
        type. Only called for complete measurements, from
        lizard-progress' adapter's html() function.

        Html_default is the html_default function of the adapter.
        Locations is a list of Location objects belonging to the
        identifiers passed in identifiers.  Layout_options mean the
        same as in a normal adapter.

        """
        pass

    def sample_image_handler(self, locations):
        """A function that implements an adapter's image() function.

        Locations is a list of Location objects belonging to the
        identifiers passed in.

        """
        pass


class PlottingData:
    """
    Class attributes:

        - data
        - baseline
        - left
        - right
        - waterlevel
        - distances
        - tops
        - bottoms
        - location
        - date
    """

    def __init__(self, data, location, date):
        self.location = location
        self.date = date

        self.baseline, self.left, self.right, self.waterlevel = self.find_base_line(data)

        self.data = self.sort_data(data, self.baseline)

        self.distances, self.tops, self.bottoms = [], [], []
        for measurement in self.data:
            x = float(measurement['x'])
            y = float(measurement['y'])

            self.distances.append(
                self.baseline.distance_to_midpoint(Point(x=x, y=y)))
            self.tops.append(float(measurement['top']))
            self.bottoms.append(float(measurement['bottom']))

    @property
    def project(self):
        return self.location.activity.project

    @staticmethod
    def sort_data(data, baseline):
        data = list(data)
        data.sort(
            key=lambda d: baseline.distance_to_midpoint(Point(d['x'], d['y'])))
        return data

    @staticmethod
    def find_base_line(data):
        codes_22 = [d for d in data
                    if d['type'] == '22']

        if len(codes_22) == 2:
            p1 = codes_22[0]
            p2 = codes_22[1]
        else:
            # It's hopeless if they aren't there, do something
            p1 = data[0]
            p2 = data[-1]

        left = Point(x=p1['x'], y=p1['y'])
        right = Point(x=p2['x'], y=p2['y'])
        line = Line(
            start=left,
            end=right)
        return line, left, right, p1['bottom']


class MetfileSpecifics(GenericSpecifics):
    extensions = ['.met']
    parser = lizard_progress.parsers.met_parser.MetParser
    linelike = True

    # Note that the response_object argument is used from exports.py, to
    # save images to a file instead of an HTTP response.
    def image_handler(self, locations, response_object=None):
        if not locations:
            # Should not happen
            logger.critical(
                "dwarsprofiel_image_handler called without measurements!")
            return

        if any(filter(lambda x: not x.complete, locations)):
            # Should not happen, incomplete dwarsprofiel measurements
            # don't have a graph in their popup.
            logger.critical(
                "dwarsprofiel_image_handler called for a graph " +
                "of noncomplete measurement!")
            return

        measurements = models.Measurement.objects.filter(
            location__in=locations)

        data = [PlottingData(m.data, m.location, m.date) for m in measurements]

        fig = ScreenFigure(525, 300)
        ax = fig.add_subplot(111)
        if len(data) == 1:
            d = data[0]
            ax.set_title(
                'Dwarsprofiel {code}, project {project}, {contractor} {date}'
                .format(code=d.location.location_code,
                        project=self.project,
                        contractor=self.organization,
                        date=d.date.strftime("%d/%m/%y")))
            ax.plot(d.distances, d.bottoms, '.-',
                    label='Zachte bodem (z2)', linewidth=1.0, color='#663300')
            ax.plot(d.distances, d.tops, '.-',
                    label='Harde bodem (z1)', linewidth=1.5, color='k')
            ax.plot([d.baseline.distance_to_midpoint(d.left),
                     d.baseline.distance_to_midpoint(d.right)],
                    [d.waterlevel, d.waterlevel],
                    label='Waterlijn',
                    linewidth=2,
                    color='b')
            ax.set_xlim([d.distances[0] - 1, d.distances[-1] + 1])
        else:
            ax.set_title(
                'Dwarsprofielen van alle projecten op locatie {code}'.format(
                    code=data[0].location.location_code))

            for i, d in enumerate(data):
                color = i / (2.0 * len(data))
                # ^^^ Multiply data len by 2 to prevent the colours from
                # becoming too light.
                ax.plot(
                    d.distances, d.bottoms, '.-', linewidth=1.0,
                    color=str(color))
                ax.plot(
                    d.distances, d.tops, '.-', linewidth=1.5,
                    color=str(color))
                ax.plot([d.baseline.distance_to_midpoint(d.left),
                         d.baseline.distance_to_midpoint(d.right)],
                        [d.waterlevel, d.waterlevel],
                        label='{project} - {date}'.format(
                            project=d.project,
                            date=d.date),
                        linewidth=2,
                        color=str(color))
                ax.set_xlim([d.distances[0] - 1, d.distances[-1] + 1])

        ax.set_xlabel('Afstand tot middelpunt watergang (m)')
        ax.set_ylabel('Hoogte (m NAP)')
        ax.legend(bbox_to_anchor=(0.5, 0.9), loc="center")
        ax.grid(True)

        response = response_object or HttpResponse(content_type='image/png')
        canvas = FigureCanvas(fig)
        canvas.print_png(response)
        return response


class OeverfotoSpecifics(GenericSpecifics):
    extensions = ['.jpg']
    parser = lizard_progress.parsers.oeverfoto_parser.OeverfotoParser
    linelike = False

    def html_handler(self, html_default, locations,
                     identifiers, layout_options):
        if not locations:
            # Should not happen
            logger.critical("foto_html_handler called without measurements!")
            return

        # Only works for the first right now
        location = locations[0]

        if not location.complete:
            logger.critical(
                "foto_html_handler called for a graph " +
                "of noncomplete measurement!")
            return

        photos = {}
        for photo in location.measurement_set.all():
            photos[photo.data] = photo

        oevers = []
        for oever in ('left', 'right'):
            if oever not in photos:
                logger.warn(("Complete measurement, but oever %s not"
                             " in photos set.") % oever)
                continue  # Should not happen

            photo = photos[oever]
            dutch = 'Linkeroever' if oever == 'left' else 'Rechteroever'
            name = '%s %s' % (location.location_code, dutch)

            oevers.append({
                'photo_url': photo.url,
                'photo_name': name,
            })

        layout_options = {'height': '400px'}
        return html_default(
            identifiers=identifiers,
            layout_options=layout_options,
            template="lizard_progress/measurement_types/photo.html",
            extra_render_kwargs={'oevers': oevers}
        )


class OeverkenmerkSpecifics(GenericSpecifics):
    extensions = ['.csv']
    parser = lizard_progress.parsers.oeverkenmerk_parser.OeverkenmerkParser
    linelike = True

    def html_handler(self, html_default, locations,
                     identifiers, layout_options):
        return html_default(
            identifiers=identifiers,
            template="lizard_progress/measurement_types/oeverkenmerk.html",
            layout_options=layout_options,
            extra_render_kwargs={
                'locations': locations})


class PeilschaalFotoSpecifics(GenericSpecifics):
    extensions = ['.jpg']
    parser = lizard_progress.parsers.peilschaal_jpg_parser.PeilschaalJpgParser
    linelike = False

    def html_handler(self, html_default, locations,
                     identifiers, layout_options):
        if not locations:
            # Should not happen
            logger.critical("foto_html_handler called without measurements!")
            return

        # Only works for the first right now
        location = locations[0]

        m = models.Measurement.objects.get(location=location)

        layout_options = {'height': '400px'}

        return html_default(
            identifiers=identifiers,
            layout_options=layout_options,
            template="lizard_progress/measurement_types/peilschaal_foto.html",
            extra_render_kwargs={'location': location.location_code,
                                 'url': m.url})


class PeilschaalMetingSpecifics(GenericSpecifics):
    extensions = ['.csv']
    parser = lizard_progress.parsers.peilschaal_csv_parser.PeilschaalCsvParser
    linelike = True

    def html_handler(self, html_default, locations,
                     identifiers, layout_options):
        return html_default(
            identifiers=identifiers,
            template="lizard_progress/measurement_types/peilschaalmeting.html",
            extra_render_kwargs={'locations': locations})


class LaboratoriumCsvSpecifics(GenericSpecifics):
    extensions = ['.csv']
    parser = lizard_progress.parsers.lab_csv_parser.LabCsvParser
    linelike = True


class RibxReinigingRioolSpecifics(GenericSpecifics):
    allow_planning_dates = True
    location_types = [models.Location.LOCATION_TYPE_PIPE,
                      models.Location.LOCATION_TYPE_MANHOLE]

    extensions = ['.ribx', '.ribxa']
    parser = lizard_progress.parsers.ribx_parser.RibxParser
    linelike = True

    def html_handler(self, html_default, locations,
                     identifiers, layout_options):
        return html_default(
            identifiers=identifiers,
            template="lizard_progress/measurement_types/ribx.html",
            extra_render_kwargs={'locations': locations})


class RibxReinigingKolkenSpecifics(RibxReinigingRioolSpecifics):
    location_types = [models.Location.LOCATION_TYPE_DRAIN]


class RibxReinigingInspectieRioolSpecifics(RibxReinigingRioolSpecifics):
    pass


class ExpectedAttachmentSpecifics(GenericSpecifics):
    extensions = [
        '.mkv', '.mp4', '.mpeg4', '.mpeg', '.mpg',  # Video
        '.jpg', '.jpeg', '.png',  # Foto
        '.ipf',  # Panoramo
    ]
    location_types = []

    parser = lizard_progress.parsers.attachment_parser.ExpectedAttachmentParser
    linelike = False


# The keys of this class are also the choices for 'implementation' of
# an AvailableMeasurementType.
AVAILABLE_SPECIFICS = {
    'dwarsprofiel': [MetfileSpecifics],
    'oeverfoto': [OeverfotoSpecifics],
    'oeverkenmerk': [OeverkenmerkSpecifics],
    'foto': [PeilschaalFotoSpecifics],
    'meting': [PeilschaalMetingSpecifics],
    'laboratorium_csv': [LaboratoriumCsvSpecifics],
    'ribx_reiniging_riool': [
        RibxReinigingRioolSpecifics, ExpectedAttachmentSpecifics],
    'ribx_reiniging_kolken': [
        RibxReinigingKolkenSpecifics, ExpectedAttachmentSpecifics],
    'ribx_reiniging_inspectie_riool': [
        RibxReinigingInspectieRioolSpecifics, ExpectedAttachmentSpecifics],
}
