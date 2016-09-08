"""Test functions from util/directories.py"""

from lizard_progress.tests.base import FixturesTestCase
from lizard_progress.tests.test_models import ActivityF
from lizard_progress.util import directories

import logging
logger = logging.getLogger(__name__)


class TestSyncDir(FixturesTestCase):

    def setUp(self):
        self.activity = ActivityF.create()

    def test_abs_sync_dir(self):
        sync_dir = directories.abs_sync_dir(self.activity)
        self.assertTrue('/ftp_readonly/autosync/' in sync_dir)
