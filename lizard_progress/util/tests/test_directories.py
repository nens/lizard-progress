"""Test functions from util/directories.py"""

from lizard_progress.tests.base import FixturesTestCase
from lizard_progress.tests.test_models import ActivityF
from lizard_progress.tests.test_review_tool import EmptyReviewProjectF
from lizard_progress.util import directories

import os
import logging
logger = logging.getLogger(__name__)

# lizard_progress.tests.test_directories

class TestSyncDir(FixturesTestCase):

    def setUp(self):
        self.activity = ActivityF.create()

    def test_abs_sync_dir(self):
        sync_dir = directories.abs_sync_dir(self.activity)
        self.assertTrue('/ftp_readonly/autosync/' in sync_dir)


class TestReviewProjectDir(FixturesTestCase):

    def setUp(self):
        self.rp = EmptyReviewProjectF.create()
        # self.pr.set_slug_and_save()

    def test_rel_reviewproject_dir(self):
        pr_dir = directories.rel_reviewproject_dir(self.rp)
        self.assertTrue(
            os.path.exists(directories.absolute(pr_dir))
        )

    def test_abs_reviewproject_files_dir(self):
        pass
