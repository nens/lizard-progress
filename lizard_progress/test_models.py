"""Tests for lizard_progress models."""

import factory

from django.test import TestCase

from lizard_progress import models
from lizard_progress.specifics import specifics


class ProjectF(factory.Factory):
    """Factory for Project models."""

    FACTORY_FOR = models.Project

    name = "Test project"
    slug = "testproject"


class TestProject(TestCase):
    """Tests for the Project model."""

    def test_specifics_unknown(self):
        """Getting specifics for an unknown project should return None."""

        project = ProjectF.build()

        self.assertEquals(project.specifics(), None)

    def test_specifics_importerror(self):
        """Getting specifics for a project with an entry point that
        can't be imported should raise an exception."""

        project = ProjectF.build()

        class MockEntryPoint(object):
            """No functionality except for failed loading."""
            name = project.slug

            def load(self):
                """I can't be loaded."""
                raise ImportError("mock")

        self.assertRaises(
            ImportError,
            lambda: specifics(project, entrypoints=[MockEntryPoint()]))
