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

    def __enter__(self):
        self.next()
        self._line_number += 1
        return self

    @property
    def line(self):
        return self._line

    @property
    def line_number(self):
        return self._line_number

    def next(self):
        self._line = self.file_object.readline()
        if self._line:
            self._line_number += 1

    def eof(self):
        return not bool(self._line)

    def __exit__(self, type, value, traceback):
        # We don't open the file in this class, so we don't close it
        # either.
        pass

