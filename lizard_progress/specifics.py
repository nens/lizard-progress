"""
Connect to classes that implement the specifics of a given project.

Usually implemented in a Lizard site.

Class/function names to be called by this module should be registered
as entrypoints in the site's setup.py, under
'lizard_progress.project_specifics'.
"""

import os
import logging
import pkg_resources

from PIL import Image
from PIL.ImageFile import ImageFile

from lizard_progress.tools import LookaheadLine

ENTRY_POINT = "lizard_progress.measurement_type_specifics"

logger = logging.getLogger(__name__)


class Specifics(object):
    def __init__(self, project):
        self.project = project
        self.__set_specifics()

    def __set_specifics(self):
        self._specifics = {}
        entrypoints = pkg_resources.iter_entry_points(group=ENTRY_POINT)

        self._slugs_in_project = dict(
            (measurement_type.mtype.slug, measurement_type)
            for measurement_type in self.project.measurementtype_set.all())

        for entrypoint in entrypoints:
            if entrypoint.name in self._slugs_in_project:
                # This may raise an ImportError, but we don't handle it
                # because that means there's a critical error anyway.
                cls = entrypoint.load()
                self._specifics[entrypoint.name] = cls

    def __instance(self, measurement_type, contractor=None):
        slug = measurement_type.mtype.slug
        cls = self._specifics[slug]
        return cls(self.project, measurement_type, contractor)

    def parsers(self, filename):
        parsers = []
        for measurement_type in self._slugs_in_project.values():
            instance = self.__instance(measurement_type)
            if filename.endswith(instance.extension):
                parsers.append(instance.parser)

        return parsers

    def html_handler(self, measurement_type, contractor):
        instance = self.__instance(measurement_type, contractor)
        if hasattr(instance, 'html_handler'):
            return instance.html_handler
        else:
            return None

    def image_handler(self, measurement_type, contractor):
        instance = self.__instance(measurement_type, contractor)

        if hasattr(instance, 'image_handler'):
            return instance.image_handler
        else:
            return None


def _open_uploaded_file(path):
    """Open file using PIL.Image.open if it is an image, otherwise
    open normally."""
    filename = os.path.basename(path)

    for ext in ('.jpg', '.gif', '.png'):
        if filename.lower().endswith(ext):
            try:
                ob = Image.open(path)
                ob.name = filename
                return ob
            except IOError:
                logger.info("IOError in Image.open(%s)!" % (path,))
                raise
    return open(path, "rU")  # U for universal line endings -- some
                             # people uploaded Mac ending files. Does
                             # mean that binaries fail.


def parser_factory(parser, project, contractor, path):
    """Sets up the parser and returns a parser instance."""

    if not issubclass(parser, ProgressParser):
        raise ValueError("Argument 'parser' of parser_factory should be "
                         "a ProgressParser instance.")

    file_object = _open_uploaded_file(path)
    return parser(project, contractor, file_object)


class ProgressParser(object):
    """Parser superclass that implementing parsers should inherit from.

    When the parser instance is created, self.project and self.contractor
    will be set. Deciding which measurement type we are dealing with is
    left to the parsers.

    The parse() method will have to be implemented by sites. It gets
    one argument: file_object, which isn't passed in but set as
    self.file_object so that other methods can access it as well. In
    case the uploaded file is a .jpg, .gif or .png, this is an opened
    PIL.Image object, with the file's basename added as
    file_object.name. Otherwise it's a file object open for reading,
    which always has a file.name attribute.

    parse() should always check whether its argument is an instance of
    PIL.ImageFile.ImageFile, and return UnsuccesfulParserResult if it
    is the wrong type.  This is because the type of object you get is
    effectively controlled by the user, and therefore untrusted.

    Parse can return three different things:
    - When it finds it is not applicable to the file in question,
      return UnSuccessfulParserResult without any arguments.
    - If it finds an error, return the same object with the error
      message as its argument. There is a helper function below that
      includes the line number in the file, if you use the also given
      helper method for parsing the file line by line.
    - In case of success, return SuccessfulParserResult with an
      iterable of Measurement objects. The calling view will add the
      full filename of the parsed file and a timestamp to them."""

    def __init__(self, project, contractor, file_object):
        self.project = project
        self.contractor = contractor
        self.file_object = file_object

    def parse(self, check_only=False):
        """Not applicable therefore return default."""
        return UnSuccessfulParserResult()

    def lookahead(self):
        """
        Helper method to go through a non-image file line by line.
        Usage:
        with self.lookahead() as la:
            while not la.eof():
                print la.line
                print la.line_number
                la.next()
        """
        if not self.file_object or isinstance(self.file_object, ImageFile):
            raise ValueError("lookahead() was passed PIL.Image object.")

        self.la = LookaheadLine(self.file_object)
        return self.la

    def error(self, key, *args):
        """Lookup the error message by its key in self.ERRORS, format it
        using *args and add the line number if possible."""

        prefix = ''
        if hasattr(self, 'file_object') and hasattr(self.file_object, 'name'):
            prefix += '%s: ' % (os.path.basename(self.file_object.name))

        if hasattr(self, 'la') and self.la:
            prefix += "Fout op regel %d: " % (self.la.line_number - 1,)
        else:
            prefix += "Fout: "

        if hasattr(self, 'ERRORS') and key in self.ERRORS:
            message = self.ERRORS[key]
        else:
            message = "Onbekende fout"

        if args:
            message = message % tuple(args)

        return UnSuccessfulParserResult(prefix + message)

    def success(self, measurements):
        """A shortcut with little utility, but if we have self.error()
        perhaps we should also have self.success()."""
        return SuccessfulParserResult(measurements)


class SuccessfulParserResult(object):
    """
    Returned by a successful parser. success is True, and measurements
    is an iterable of Measurement objects that were inserted by the
    parser. Lizard_progress will update them with filename of the file
    that was parsed (after moving it to its eventual destination) and
    a timestamp.

    Note that measurements can be empty, if the parser was called with
    check_only=True (from a checking script, for instance).
    """
    def __init__(self, measurements):
        self.success = True
        self.measurements = tuple(measurements)


class UnSuccessfulParserResult(object):
    """
    Returned by an unsuccessful parser. Error is an error message.
    """
    def __init__(self, error=None):
        self.success = False
        self.error = error

    def __str__(self):
        return "UnSuccessfulParserResult: {}".format(self.error)


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
