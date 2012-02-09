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

    def __init__(self, filename):
        self.filename = filename

    def __enter__(self):
        self.file = open(self.filename)
        self.next()
        return self

    @property
    def line(self):
        return self._line

    def next(self):
        self._line = self.file.readline()

    def eof(self):
        return not bool(self._line)

    def __exit__(self, type, value, traceback):
        self.file.close()
