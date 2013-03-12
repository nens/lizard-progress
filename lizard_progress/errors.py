# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

"""Helper functions and classes for error handling.

We implement many checks on MET files. Some of these checks are
relevant to all organizations that receive MET files, but others only
for some of them."""

# Python 3 is coming
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from lizard_progress import models


class ErrorConfiguration(object):
    """A helper object. An instance of this class can be called as if
    it were a function, with an error code as an argument. It returns
    True if the check relating to that code should be performed, False
    if it shouldn't."""

    def __init__(self, project, measurement_type):
        self.project = project
        self.measurement_type = measurement_type
        self.init_error_sets()

    def init_error_sets(self):
        """Set the two error sets, of existing error codes and of
        codes to check in this project."""
        self.existing_error_codes = set(
            error_message.error_code
            for error_message in models.ErrorMessage.objects.all())

        self.codes_to_check = set(
            error_message.error_code
            for error_message in self.project.organization.errors_set())

    def __call__(self, error_code):
        if self.measurement_type.slug != 'dwarsprofiel':
            # For now, these differentiated checks only exist for MET files.
            # Other measurement types always get True.
            return True

        if error_code not in self.existing_error_codes:
            # If an error_code isn't configured, we assume it's a check that
            # always happens.
            return True

        return error_code in self.codes_to_check
