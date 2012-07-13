"""A module containing things that had no obvious other home."""

import os
import logging
import shutil
import time

logger = logging.getLogger(__name__)

class LookaheadLine(object):
    """
    Usage:

    lookahead = LookaheadLine(filename)
    with LookaheadLine(filename) as la:
        if la.line.startswith("<PROFIEL"):
             # ...Parse line...
             la.next()
             while la.line.startswith("<METING")
                 # ...Parse metingen...
                 la.next()

    It helps to create a "lookahead-one-line" parser.
    """

    def __init__(self, file_object):
        self.file_object = file_object
        self._line_number = 0
        self._line = None

    def __enter__(self):
        self.next()
        self._line_number += 1
        return self

    @property
    def line(self):
        """Current line (string)."""
        return self._line

    @property
    def line_number(self):
        """Current line number (int)."""
        return self._line_number

    def next(self):
        """Read the next line. Increase the line number, unless the
        end of file was reached."""
        self._line = self.file_object.readline()
        if self._line:
            self._line_number += 1

    def eof(self):
        """Test whether the end of file was reached (boolean)."""
        return not bool(self._line)

    def __exit__(self, exception_type, value, traceback):
        """Leave context manager."""
        # We don't open the file in this class, so we don't close it
        # either.
        pass


class MovedFile(object):
    """The silly thing is that the parsers sometimes do checks on the
    format of filenames, and then lizard-progress saves the files with
    a timestamp added to the front, making the tests always fail if
    they are repeated later.

    We need to run the repeated tests on a version of the file that
    has the untimestamped name. We put it in /tmp and use this context
    manager to ensure that it is deleted afterwards."""

    def __init__(self, path):
        self.path = path

    def __enter__(self):
        self.new_path = os.path.join(
            '/tmp',
            orig_from_unique_filename(os.path.basename(self.path)))
        shutil.copy(self.path, self.new_path)

        return self.new_path

    def __exit__(self, _exc_type, _exc_value, _traceback):
        os.remove(self.new_path)


def unique_filename(orig_filename, seq):
    """Create a unique filenmae based on the original and a sequence
    number."""
    return ('%s-%d-%s' % (time.strftime('%Y%m%d-%H%M%S'),
                          seq, orig_filename))


def orig_from_unique_filename(filename):
    """Restore the original filename (remove the time and sequence
    number)."""
    parts = filename.split('-')
    if len(parts) < 4:
        # We inserted 3 dashes in unique_filename(), there should be
        # at least 4 parts.
        raise ValueError(
            "Filename '%s' doesn't look like it came from unique_filename()."
            % (filename,))

    return '-'.join(parts[3:])
