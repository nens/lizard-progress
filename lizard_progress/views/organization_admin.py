from django import http
from django.core.urlresolvers import reverse

from lizard_ui.views import UiView

from lizard_progress import configuration
from lizard_progress.views.views import KickOutMixin


class OrganizationAdminView(KickOutMixin, UiView):
    template_name = "lizard_progress/organization_admin.html"


class OrganizationAdminConfiguration(OrganizationAdminView):
    """Boundary values for checks"""
    template_name = "lizard_progress/organization_config.html"

    def config_options(self):
        config = configuration.Configuration(
            organization=self.organization)
        return list(config.options())

    def post(self, request, *args, **kwargs):
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
