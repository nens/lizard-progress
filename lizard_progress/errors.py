# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

"""Helper functions and classes for error handling. This module knows
which error checks should be used for some project; configuration.py
knows configuration options for each check.

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
    """A helper object to decide which error checks should be used.

    To check whether a given error code should be used, use the 'in'
    operator.

    It returns True if the check relating to that code should be
    performed, False if it shouldn't."""

    def __init__(self, project, organization, measurement_type):
        """Give either a project or an organization, not both.

        The usual situation is that the parsers wants to know which
        checks to use, in that case it will give the project. The
        project is also given when the options need to be shown for
        configuring inside some project. The organization is used when
        configuring the default values for some organization; we need
        to know which checks to show the configuration for there."""

        self.project = project
        self.organization = organization
        self.measurement_type = measurement_type
        self.init_error_sets()

    def init_error_sets(self):
        """Set the two error sets, of existing error codes and of
        codes to check in this project."""
        self.existing_error_codes = set(
            error_message.error_code
            for error_message in models.ErrorMessage.objects.all())

        organization = self.organization or self.project.organization
        self.codes_to_check = set(
            error_message.error_code
            for error_message in organization.errors.all())

    def __contains__(self, error_code):
        if self.measurement_type.mtype.implementation_slug != 'dwarsprofiel':
            # For now, these differentiated checks only exist for MET files.
            # Other measurement types always get True.
            return True

        if error_code not in self.existing_error_codes:
            # If an error_code isn't configured, we assume it's a check that
            # always happens.
            return True

        return error_code in self.codes_to_check

    def wants_sorted_measurements(self):
        """This is a specific method used for Dwarsprofiel measurements.

        Sometimes <meting> lines are not assumed to be in the right
        order, and code has to sort them themselves. Whether it does
        so or not is controlled by the presence of the check on
        MET_Z1_DIFFERENCE_TOO_LARGE in this configuration, because
        that is a check that always does this sorting. The rule is: if
        a project uses that check, then it must like sorting."""

        return 'MET_Z1_DIFFERENCE_TOO_LARGE' in self
