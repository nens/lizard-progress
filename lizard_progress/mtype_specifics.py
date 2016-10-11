"""Each measurement type has specifics that define its behavior, like
how to show a measurement in a popup, or whether an uploaded file
should be treated as linelike or as binary.

This module defines a Specifics object for each measurement type.
"""

import logging

from django.core.urlresolvers import reverse
from django.http import HttpResponse

import lizard_progress.parsers.attachment_parser
import lizard_progress.parsers.lab_csv_parser
import lizard_progress.parsers.met_parser
import lizard_progress.parsers.oeverfoto_parser
import lizard_progress.parsers.oeverkenmerk_parser
import lizard_progress.parsers.peilschaal_csv_parser
import lizard_progress.parsers.peilschaal_jpg_parser
import lizard_progress.parsers.ribx_parser

from lizard_progress import models
from lizard_progress import crosssection_graph

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

        if any(not location.complete for location in locations):
            # Should not happen, incomplete dwarsprofiel measurements
            # don't have a graph in their popup.
            logger.critical(
                "dwarsprofiel_image_handler called for a graph " +
                "of noncomplete measurement!")
            return

        measurements = models.Measurement.objects.filter(
            location__in=locations)

        canvas = crosssection_graph.graph(locations[0], measurements)

        response = response_object or HttpResponse(content_type='image/png')
        canvas.print_png(response)
        return response

    def html_handler(self, html_default, locations,
                     identifiers, layout_options):
        location = locations[0]
        organization = location.activity.project.organization

        multiple_projects_graph_url = None
        if location.close_by_locations_of_same_organisation().count() > 1:
            multiple_projects_graph_url = reverse(
                'crosssection_graph', kwargs=dict(
                    organization_id=organization.id,
                    location_id=location.id))

        return html_default(
            identifiers=identifiers,
            layout_options=layout_options,
            template="lizard_progress/measurement_types/metfile.html",
            extra_render_kwargs=dict(
                multiple_projects_graph_url=multiple_projects_graph_url))


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
                                 'url': m.get_absolute_url()})


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
    parser = lizard_progress.parsers.ribx_parser.RibxReinigingKolkenParser


class RibxReinigingInspectieRioolSpecifics(RibxReinigingRioolSpecifics):
    parser = \
        lizard_progress.parsers.ribx_parser.RibxReinigingInspectieRioolParser


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
