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

    def post(self, request, *args, **kwargs):
        if not self.user_has_manager_role():
            raise PermissionDenied()

        redirect = http.HttpResponseRedirect(reverse(
                "lizard_progress_admin_organization_errorconfiguration"))

        for key, option in configuration.CONFIG_OPTIONS.iteritems():
            value_str = request.POST.get(key, '')
            try:
                value = option.translate(value_str)
                # No error, set it
                config = configuration.Configuration(
                    organization=self.organization)
                config.set(option, value)
            except ValueError:
                pass

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
