"""Functions for testing the parsers."""

import datetime

from django.test import TestCase

from lizard_progress.parsers.met_parser import MetParser
from lizard_progress.specifics import UnSuccessfulParserResult
from lizard_progress.tests.test_models import ProjectF, ContractorF


def parser_factory(parser, file_object=None):
    """Instantiate a parser object."""
    project = ProjectF()
    contractor = ContractorF(project=project)
    return parser(project, contractor, file_object)

PROFIEL_ID = 'N-BR00002457_665'
PROFIEL_STR = 'PROFIEL_665'
PEILWAARDE = '0.00'
DATE = '20120113'
UNIT = 'NAP'
ABS_OR_REL = 'ABS'
X = '141367.613'
Y = '463410.438'
Z_VALUES = '2'
COORDS = 'XY'


def make_profiel_line(
    profiel_id=PROFIEL_ID,
    profiel_str=PROFIEL_STR,
    date_str=DATE,
    peilwaarde=PEILWAARDE,
    unit=UNIT,
    abs_or_rel=ABS_OR_REL,
    z_values=Z_VALUES,
    coords=COORDS,
    x=X,
    y=Y):
    """Function to quickly make a <profiel> line for testing."""
    return ("<PROFIEL>%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,\n" %
            (profiel_id, profiel_str, date_str, peilwaarde, unit,
             abs_or_rel, z_values, coords, x, y))

METING_TYPE = '22'


def make_meting_line(
    meting_type=METING_TYPE,
    x=X,
    y=Y
    ):
    """Function to quickly make a <meting> line for testing."""
    return (("<METING>%s,999,%s,%s,1.305,1.305</METING>\n") %
            (meting_type, x, y))


class TestMetParser(TestCase):
    """Test the MetParser."""

    def _profiel_line_returns_error(self, profiel_line, contains=None):
        """Helper function that checks whether some profiel_line returns
        a correct error, and optionally whether the error message contains
        some string (case insensitive)."""

        parser = parser_factory(MetParser)
        ((profielid, date), error) = parser.parse_profiel_line(
            profiel_line)

        self.assertEquals(profielid, None)
        self.assertEquals(date, None)
        self.assertNotEquals(error, None)
        self.assertTrue(isinstance(error, UnSuccessfulParserResult))
        self.assertFalse(error.success)
        self.assertTrue(error.error)
        if contains:
            # Check whether 'contains' occurs without caring about case
            self.assertTrue(contains.lower() in error.error.lower())

    def test_make_profiel_line(self):
        """Let's test the helper function itself too, was useful when it
        was made..."""
        return self.assertEquals(
            make_profiel_line(),
            ('<PROFIEL>N-BR00002457_665,PROFIEL_665,20120113,'
             '0.00,NAP,ABS,2,XY,141367.613,463410.438,\n'))

    def test_correct_profiel_line(self):
        """Let's test one correct line and see if it returns the right data."""
        parser = parser_factory(MetParser)

        ((profielid, date), error) = parser.parse_profiel_line(
            make_profiel_line())

        self.assertEquals(profielid, 'N-BR00002457_665')
        self.assertEquals(date, datetime.datetime(2012, 1, 13))
        self.assertEquals(error, None)

    def test_empty_profiel_line(self):
        """An empty line should return an error. It will start with
        <PROFIEL> otherwise this function wouldn't be called."""
        self._profiel_line_returns_error('<PROFIEL>')

    def test_wrong_peilwaarde(self):
        """Peilwaarde must be 0"""
        self._profiel_line_returns_error(
            make_profiel_line(peilwaarde='1.0'),
            contains='peilwaarde')

    def test_wrong_date(self):
        """Test wrongly formatted date string."""
        self._profiel_line_returns_error(
            make_profiel_line(date_str='2012-01-13'),
            contains='datum')

    def test_wrong_unit(self):
        """For HDSR, unit must be 'NAP'."""
        self._profiel_line_returns_error(
            make_profiel_line(unit='ANP'), contains='NAP')

    def test_wrong_abs_or_rel(self):
        """For HDSR, must be 'ABS'."""
        self._profiel_line_returns_error(
            make_profiel_line(abs_or_rel='REL'), contains='ABS')

    def test_wrong_z_values(self):
        """For HDSR, must be '2'."""
        self._profiel_line_returns_error(
            make_profiel_line(z_values='3'), contains='2')

    def test_wrong_coords(self):
        """For HDSR this field should contain 'XY'."""
        self._profiel_line_returns_error(
            make_profiel_line(coords='YX'), contains='XY')

    def test_make_meting_line(self):
        """Test the helper function."""
        self.assertEquals(
            make_meting_line(),
            "<METING>22,999,141367.613,463410.438,1.305,1.305</METING>\n")
