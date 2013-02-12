"""
Connect to classes that implement the specifics of a given project.

Usually implemented in a Lizard site.

Class/function names to be called by this module should be registered
as entrypoints in the site's setup.py, under
'lizard_progress.project_specifics'.
"""

import os
import logging

from PIL import Image
from PIL.ImageFile import ImageFile

from lizard_progress.tools import LookaheadLine

ENTRY_POINT = "lizard_progress.measurement_type_specifics"

logger = logging.getLogger(__name__)


class Specifics(object):
    def __init__(self, project, entrypoints=None):
        self.project = project
        self.__set_specifics(entrypoints)

    def __set_specifics(self, entrypoints=None):
        # Only import it now to avoid circular imports (models
        # imports this, this imports mtype_specifics, that imports
        # parsers, those import models).
        from lizard_progress.mtype_specifics import AVAILABLE_SPECIFICS

        self._specifics = {}
        self._slugs_in_project = dict(
            (measurement_type.mtype.slug, measurement_type)
            for measurement_type in self.project.measurementtype_set.all())

        for slug in self._slugs_in_project:
            # If the key doesn't exist in AVAILABLE_SPECIFICS, we just
            # let it throw the exception because something is wrong
            # anyway.
            self._specifics[slug] = AVAILABLE_SPECIFICS[slug]

    def __instance(self, measurement_type, contractor=None):
        slug = measurement_type.mtype.slug
        cls = self._specifics[slug]
        return cls(self.project, measurement_type, contractor)

    def parsers(self, filename):
        parsers = []
        for measurement_type in self._slugs_in_project.values():
            instance = self.__instance(measurement_type)
            if filename.lower().endswith(instance.extension):
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
