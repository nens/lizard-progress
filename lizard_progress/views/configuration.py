import logging

from django import http
from django.core.urlresolvers import reverse

from lizard_progress.views.views import ProjectsView

from lizard_progress import configuration

logger = logging.getLogger(__name__)


class ConfigurationView(ProjectsView):
    template_name = 'lizard_progress/project_configuration_page.html'

    def config_options(self):
        config = configuration.Configuration(
            project=self.project)
        return list(config.options())

    def post(self, request, *args, **kwargs):
        redirect = http.HttpResponseRedirect(reverse(
                "lizard_progress_project_configuration_view",
                kwargs={'project_slug': self.project.slug}))

        if self.project.superuser != self.user:
            return redirect

        for key in configuration.CONFIG_OPTIONS:
            option = configuration.CONFIG_OPTIONS[key]
            value_str = request.POST.get(key, '')
            try:
                value = option.translate(value_str)
                # No error, set it
                config = configuration.Configuration(project=self.project)
                config.set(option, value)
            except ValueError:
                pass

        return redirect
