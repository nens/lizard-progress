from django.test import TestCase


DEFAULT_FIXTURES = (
    'userroles.json',
    'notification_types.json',
    'errormessages.json'
)


class FixturesTestCase(TestCase):
    """TestCase with all our necessary fixtures, to be the base class of
    all normal testcases."""

    fixtures = DEFAULT_FIXTURES
