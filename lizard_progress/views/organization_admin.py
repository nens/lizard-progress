# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

"""Views for the organization config defaults."""

# Python 3 is coming
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from collections import defaultdict

from django import http
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse

from lizard_progress.views.views import ProjectsView
from lizard_progress import configuration

from lizard_progress import models

import logging

logger = logging.getLogger(__name__)


class OrganizationAdminConfiguration(ProjectsView):
    """Boundary values for checks"""
    template_name = "lizard_progress/organization_config.html"

    def config_options(self):
        config = configuration.Configuration(
            organization=self.organization)
        return list(config.options())

    def config_option_blocks(self):
        option_blocks = defaultdict(list)

        options = [option[0] for option in self.config_options()]

        mtypes = list(self.organization.visible_available_measurement_types())
        logger.debug("config_option_blocks: mtypes = {}".format(mtypes))

        for option in options:
            logger.debug(">>> option: {}".format(option))
            if option.all_measurement_types:
                logger.debug("option {} does not apply to mtypes"
                             .format(option[0]))
                option_blocks[('', '')].append(
                    (option, option.default_for(self.organization, None)))
            else:
                logger.debug("option {} DOES not apply to mtypes!"
                             .format(option))
                for mtype in mtypes:
                    applies = option.applies_to(mtype)
                    logger.debug("Testing mtype {}... {}".format(
                        mtype, applies))
                    if applies:
                        option_blocks[(mtype.slug, unicode(mtype))].append(
                            (option,
                             option.default_for(self.organization, mtype)))

        # Note that defaultdicts don't work well with Django's templates,
        # convert to a normal dict before returning.
        return dict(option_blocks.items())

    def post(self, request, *args, **kwargs):
        if not self.user_has_manager_role():
            raise PermissionDenied()

        redirect = http.HttpResponseRedirect(reverse(
            "lizard_progress_admin_organization_errorconfiguration"))

        mtype_slug = request.POST.get('mtype_slug', '')
        mtype = None
        if mtype_slug:
            try:
                mtype = models.AvailableMeasurementType.objects.get(
                    slug=mtype_slug)
            except models.AvailableMeasurementType.DoesNotExist:
                pass
        logger.debug(
            "In POST of organization admin; mtype_slug={}, mtype={}".format(
                mtype_slug, mtype))

        for key, option in configuration.CONFIG_OPTIONS.iteritems():
            if mtype_slug and mtype:
                if not option.applies_to(mtype):
                    continue
            else:
                if not option.all_measurement_types:
                    continue
            try:
                value_str = request.POST.get(key, '')
                logger.debug("Converting '{}'...".format(value_str))
                value = option.translate(value_str)
            except ValueError:
                value = None

            if value is not None:
                # No error, set it
                config = configuration.Configuration(
                    organization=self.organization,
                    measurement_type=mtype)
                config.set(option, value)

        return redirect


class VisibleMeasurementTypes(ProjectsView):
    """Manage which measurement types are visible."""

    template_name = "lizard_progress/visible_measurement_types.html"

    def allowed_measurement_types(self):
        """Return all MeasurementTypeAllowed objects for this organization."""
        return models.MeasurementTypeAllowed.objects.filter(
            organization=self.organization).order_by(
            'mtype__name').select_related()

    def post(self, request, *args, **kwargs):
        if not self.user_is_manager():
            raise PermissionDenied()

        slug = request.POST.get('slug')
        new_visibility = request.POST.get('new_visibility')

        if slug is not None and new_visibility is not None:
            self.update_visibility(slug, new_visibility)

        return http.HttpResponseRedirect(reverse(
            "lizard_progress_editvisibility"))

    def update_visibility(self, slug, new_visibility):
        logger.debug("Updating visibility: {} {}".format(
            slug, new_visibility))

        organization = self.profile.organization

        try:
            amtype = models.AvailableMeasurementType.objects.get(
                slug=slug)
        except models.AvailableMeasurementType.DoesNotExist:
            # No such measurement type. Just do nothing.
            return

        try:
            allowed = models.MeasurementTypeAllowed.objects.get(
                organization=organization, mtype=amtype)
        except models.MeasurementTypeAllowed.DoesNotExist:
            # If it doesn't exist, then this organization isn't
            # allowed to see this measurement type. Just do nothing.
            return

        try:
            allowed.visible = bool(int(new_visibility))
            allowed.save()
        except ValueError:
            # No int given
            pass
