"""
Connection to lizard_progress. This module implements the
HDSR-specific details.
"""

import logging
from math import sqrt

from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas

from django.http import HttpResponse

from metfilelib.util.linear_algebra import Line, Point

import lizard_progress.parsers.met_parser
import lizard_progress.parsers.oeverfoto_parser
import lizard_progress.parsers.oeverkenmerk_parser
import lizard_progress.parsers.peilschaal_jpg_parser
import lizard_progress.parsers.peilschaal_csv_parser
import lizard_progress.parsers.lab_csv_parser

from lizard_progress.models import Measurement
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

    def __init__(self, project, measurement_type, contractor=None):
        self.project = project
        self.measurement_type = measurement_type
        self.contractor = contractor

    ## The below are named "sample_" so that the adapter can see that
    ## the real html_handler and image_handler aren't implemented.  In
    ## your own Specifics objects, they need to be named
    ## 'html_handler' and 'image_handler'.

    def sample_html_handler(self, html_default, scheduled_measurements,
                            identifiers, layout_options):
        """
        A function that can generate popup HTML for this measurement
        type. Only called for complete measurements, from
        lizard-progress' adapter's html() function.

        Html_default is the html_default function of the adapter.
        Scheduled_measurements is a list of ScheduledMeasurement
        objects belonging to the identifiers passed in identifiers.
        Layout_options mean the same as in a normal adapter.
        """
        pass

    def sample_image_handler(self, scheduled_measurements):
        """
        A function that implements an adapter's image() function.

        Scheduled_measurements is a list of ScheduledMeasurement
        objects belonging to the identifiers passed in.
        """
        pass


class MetfileSpecifics(GenericSpecifics):
    extension = '.met'
    parser = lizard_progress.parsers.met_parser.MetParser
    linelike = True

    # Note that the response_object argument is used from exports.py, to
    # save images to a file instead of an HTTP response.
    def image_handler(self, scheduled_measurements, response_object=None):
        if not scheduled_measurements:
            # Should not happen
            logger.critical(
                "dwarsprofiel_image_handler called without measurements!")
            return

        # Currently only works for the first
        sm = scheduled_measurements[0]

        if not sm.complete:
            # Should not happen, incomplete dwarsprofiel measurements
            # don't have a graph in their popup.
            logger.critical(
                "dwarsprofiel_image_handler called for a graph " +
                "of noncomplete measurement!")
            return

        try:
            m = Measurement.objects.get(scheduled=sm)
        except Measurement.DoesNotExist:
            # Again, should not happen.
            logger.critical(
                "ScheduledMeasurement id=%d is complete, but there " +
                "is no Measurement for it!" % sm.id)
            return

        data = m.data
        baseline, left, right, waterlevel = self.find_base_line(data)
        data = self.sort_data(data, baseline)

        distances, tops, bottoms = [], [], []
        for measurement in data:
            x = float(measurement['x'])
            y = float(measurement['y'])

            distances.append(baseline.distance_to_midpoint(Point(x=x, y=y)))
            tops.append(float(measurement['top']))
            bottoms.append(float(measurement['bottom']))

        fig = ScreenFigure(525, 300)
        ax = fig.add_subplot(111)
        ax.set_title(
            'Dwarsprofiel {code}, project {project}, {contractor} {date}'
            .format(code=sm.location.location_code,
                    project=sm.project,
                    contractor=sm.contractor.organization,
                    date=m.date.strftime("%d/%m/%y")))

        ax.set_xlabel('Afstand tot middelpunt watergang (m)')
        ax.set_ylabel('Hoogte (m NAP)')
        ax.plot(distances, bottoms, '.-',
                label='Zachte bodem (z2)', linewidth=1.0, color='#663300')
        ax.plot(distances, tops, '.-',
                label='Harde bodem (z1)', linewidth=1.5, color='k')
        ax.plot([baseline.distance_to_midpoint(left),
                 baseline.distance_to_midpoint(right)],
                [waterlevel, waterlevel],
                label='Waterlijn',
                linewidth=2,
                color='b')

        ax.legend(bbox_to_anchor=(0.5, 0.9), loc="center")
        ax.set_xlim([distances[0] - 1, distances[-1] + 1])
        ax.grid(True)

        response = response_object or HttpResponse(content_type='image/png')
        canvas = FigureCanvas(fig)
        canvas.print_png(response)
        return response

    def sort_data(self, data, baseline):
        data = list(data)
        data.sort(
            key=lambda d: baseline.distance_to_midpoint(Point(d['x'], d['y'])))
        return data

    def find_base_line(self, data):
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


class OeverfotoSpecifics(GenericSpecifics):
    extension = '.jpg'
    parser = lizard_progress.parsers.oeverfoto_parser.OeverfotoParser
    linelike = False

    def html_handler(self, html_default, scheduled_measurements,
                     identifiers, layout_options):
        if not scheduled_measurements:
            # Should not happen
            logger.critical("foto_html_handler called without measurements!")
            return

        # Only works for the first right now
        sm = scheduled_measurements[0]

        if not sm.complete:
            logger.critical(
                "foto_html_handler called for a graph " +
                "of noncomplete measurement!")
            return

        photos = {}
        for photo in sm.measurement_set.all():
            photos[photo.data] = photo

        oevers = []
        for oever in ('left', 'right'):
            if not oever in photos:
                logger.warn(("Complete measurement, but oever %s not"
                             " in photos set.") % oever)
                continue  # Should not happen

            photo = photos[oever]
            dutch = 'Linkeroever' if oever == 'left' else 'Rechteroever'
            name = '%s %s' % (sm.location.location_code, dutch)

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
    extension = '.csv'
    parser = lizard_progress.parsers.oeverkenmerk_parser.OeverkenmerkParser
    linelike = True

    def html_handler(self, html_default, scheduled_measurements,
                         identifiers, layout_options):
        return html_default(
            identifiers=identifiers,
            template="lizard_progress/measurement_types/oeverkenmerk.html",
            layout_options=layout_options,
            extra_render_kwargs={
                'scheduled_measurements': scheduled_measurements})


class PeilschaalFotoSpecifics(GenericSpecifics):
    extension = '.jpg'
    parser = lizard_progress.parsers.peilschaal_jpg_parser.PeilschaalJpgParser
    linelike = False

    def html_handler(self, html_default, scheduled_measurements,
                          identifiers, layout_options):
        if not scheduled_measurements:
            # Should not happen
            logger.critical("foto_html_handler called without measurements!")
            return

        # Only works for the first right now
        sm = scheduled_measurements[0]

        m = Measurement.objects.get(scheduled=sm)

        layout_options = {'height': '400px'}

        return html_default(
            identifiers=identifiers,
            layout_options=layout_options,
            template="lizard_progress/measurement_types/peilschaal_foto.html",
            extra_render_kwargs={'location': sm.location.location_code,
                                 'url': m.url})


class PeilschaalMetingSpecifics(GenericSpecifics):
    extension = '.csv'
    parser = lizard_progress.parsers.peilschaal_csv_parser.PeilschaalCsvParser
    linelike = True

    def html_handler(self, html_default, scheduled_measurements,
                     identifiers, layout_options):
        return html_default(
            identifiers=identifiers,
            template="lizard_progress/measurement_types/peilschaalmeting.html",
            extra_render_kwargs={
                'scheduled_measurements': scheduled_measurements})


class LaboratoriumCsvSpecifics(GenericSpecifics):
    extension = '.csv'
    parser = lizard_progress.parsers.lab_csv_parser.LabCsvParser
    linelike = True


AVAILABLE_SPECIFICS = {
    'dwarsprofiel': MetfileSpecifics,
    'oeverfoto': OeverfotoSpecifics,
    'oeverkenmerk': OeverkenmerkSpecifics,
    'foto': PeilschaalFotoSpecifics,
    'meting': PeilschaalMetingSpecifics,
    'laboratorium_csv': LaboratoriumCsvSpecifics
    }
