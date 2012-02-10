"""
Connect to classes that implement the specifics of a given project.

Usually implemented in a Lizard site.

Class/function names to be called by this module should be registered
as entrypoints in the site's setup.py, under
'lizard_progress.project_specifics'.
"""

import logging
import pkg_resources

ENTRY_POINT = "lizard_progress.project_specifics"

logger = logging.getLogger(__name__)


def specifics(project):
    for entrypoint in pkg_resources.iter_entry_points(
        group=ENTRY_POINT):
        if entrypoint.name == project.slug:
            try:
                cls = entrypoint.load()
                return cls(project)
            except ImportError, e:
                logger.warn("ImportError trying to find " +
                            "specific implementation: %s" % e)
                logger.warn("Using defaults.")
                return GenericSpecifics(project)


class SuccessfulParserResult(object):
    """
    Returned by a successful parser. success is True, and
    'result_path' contains the path that the file should be moved to.
    """
    def __init__(self, result_path):
        self.success = True
        self.result_path = result_path


class UnSuccessfulParserResult(object):
    """
    Returned by an unsuccessful parser. Error is an error message.
    """
    def __init__(self, error):
        self.success = False
        self.error = error


class GenericSpecifics(object):
    """
    The goal of this class is threefold:
    - Have a specifics implementation we can use for testing
    - Have an implementation that can be used as a blueprint (you can
      inherit this class, if you wish).
    - To have a class with this name.
    """

    def __init__(self, project):
        self.project = project

    def upload_file_types(self, project):
        """
        Return a tuple of 2-tuples (filedescription, extension) to be
        used in the file upload dialog. E.g. return (("CSV files",
        "csv")).
        """

        return ()

    def parsers(self, filename):
        """
        Return a tuple of functions that will try to parse an uploaded
        file, in the order in which they are given (say to return only
        a single parser, based on the filename's extension).

        Parsers should return an instance of either
        SuccessfulParserResult or UnSuccessfulParserResult.
        """

        return ()

    def html_handler(self, measurement_type, contractor, project):
        return None

    def image_handler(self, measurement_type, contractor, project):
        return None

    def sample_html_handler(self, html_default, scheduled_measurements,
                            identifiers, layout_options):
        # Html_default is the html_default function of the adapter
        # scheduled_measurements is a list of ScheduledMeasurement objects
        #     belonging to the identifiers passed in
        # identifiers, layout_options mean that same
        # as in a normal adapter.
        pass

    def sample_image_handler(self, scheduled_measurements):
        # scheduled_measurements is a list of ScheduledMeasurement objects
        #     belonging to the identifiers passed in
        pass
