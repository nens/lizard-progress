"""Test functions from util/image.py"""

from django.test import TestCase
from PIL import Image
from pkg_resources import resource_filename  # pylint: disable=E0611

from lizard_progress.util.image import get_exif_data
from lizard_progress.util.image import get_lat_lon

import logging
logger = logging.getLogger(__name__)


class TestExif(TestCase):
    """Test functions for EXIF data from images"""

    def test_exif(self):
        """Read exif data from a known test image."""

        filename = resource_filename(
            "lizard_progress", "/testdata/IMG_0366.JPG")
        image = Image.open(filename)
        exif_data = get_exif_data(image)
        lat, lon = get_lat_lon(exif_data)

        self.assertEquals(lat, 52.08)
        self.assertEquals(lon, 5.011166666666667)
