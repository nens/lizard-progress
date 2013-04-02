# (c) Nelen & Schuurmans. GPL licensed, see LICENSE.txt.

"""Views concerned with downloading files."""

import logging
import mimetypes
import os
import platform

from django.conf import settings
from django.core.urlresolvers import reverse
from django import http
from django.http import HttpResponse
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.views.generic import View
from django.views.static import serve

from lizard_ui.layout import Action

from lizard_progress import models
from lizard_progress import tasks
from lizard_progress.util import directories
from lizard_progress.models import Contractor
from lizard_progress.models import Project
from lizard_progress.models import has_access
from lizard_progress.views.upload import UploadReportsView
from lizard_progress.views.views import ProjectsView

logger = logging.getLogger(__name__)


APP_LABEL = Project._meta.app_label


class DownloadHomeView(ProjectsView):
    """This view offers links to downloadable project artifacts.

    If the user does not have sufficient rights,
    a `HttpResponseForbidden` is returned.
    """
    template_name = "lizard_progress/download_home.html"

    def _make_url(self, filetype, project, contractor, path):
        return reverse('lizard_progress_downloadview', kwargs={
                'filetype': filetype,
                'project_slug': project.slug,
                'contractor_slug': contractor.slug if contractor else 'x',
                'filename': os.path.basename(path)
                })

    def _organization_files(self):
        for path in directories.files_in(
            directories.organization_files_dir(self.project.organization)):
            yield {
                'type': 'Handleidingen e.d.',
                'filename': os.path.basename(path),
                'size': directories.human_size(path),
                'url': self._make_url('organization',
                                      self.project,
                                      None,
                                      path)
                }

    def _reports_files(self):
        for contractor in self.project.contractor_set.all():
            if has_access(self.user, self.project, contractor):
                for path in directories.files_in(
                    directories.reports_dir(self.project, contractor)):
                        yield {
                        'type': 'Rapporten {0}'.format(
                            contractor.organization.name),
                        'filename': os.path.basename(path),
                        'size': directories.human_size(path),
                        'url': self._make_url('reports',
                                              self.project,
                                              contractor,
                                              path)
                        }

    def _results_files(self):
        for contractor in self.project.contractor_set.all():
            if has_access(self.user, self.project, contractor):
                for path in directories.files_in(
                    directories.results_dir(self.project, contractor)):
                        yield {
                        'type': 'Resultaten {0}'.format(
                            contractor.organization.name),
                        'filename': os.path.basename(path),
                        'size': directories.human_size(path),
                        'url': self._make_url('results',
                                              self.project,
                                              contractor,
                                              path)
                        }

    def _location_shapefile_files(self):
        for contractor in self.project.contractor_set.all():
            if has_access(self.user, self.project, contractor):
                for path in directories.files_in(
                    directories.location_shapefile_dir(
                        self.project, contractor)):
                        yield {
                            'type': 'Meetlocatie shapefile '.format(
                                contractor.organization.name),
                            'filename': os.path.basename(path),
                            'size': directories.human_size(path),
                            'url': self._make_url('organization',
                                                  self.project,
                                                  contractor,
                                                  path)
                        }

    def files(self):
        if not hasattr(self, '_files'):
            try:
                self._files = {
                    'organization': list(self._organization_files()),
                    'reports': list(self._reports_files()),
                    'results': list(self._results_files()),
                    'shapefile': list(self._location_shapefile_files())
                    }
            except Exception as e:
                logger.debug(e)
        return self._files

    def csv(self):
        """Links to CSV downloads. One per contractor."""

        if hasattr(self, '_csvs'):
            return self._csvs

        csvs = []

        for contractor in Contractor.objects.filter(project=self.project):
            if has_access(self.request.user, self.project, contractor):
                url = reverse(
                    'lizard_progress_dashboardcsvview',
                    kwargs={
                        'project_slug': self.project_slug,
                        'contractor_slug': contractor.slug,
                        })

                csvs.append((contractor, url))

        self._csvs = csvs
        return csvs

    def exports(self):
        return models.ExportRun.all_in_project(
            self.project, self.request.user)

    @property
    def breadcrumbs(self):
        """Breadcrumbs for this page."""
        crumbs = super(DownloadHomeView, self).breadcrumbs

        crumbs.append(
            Action(
                description=("Downloads for {project}"
                             .format(project=self.project.name)),
                name="Download",
                url=reverse(
                    'lizard_progress_downloadhomeview',
                    kwargs={'project_slug': self.project_slug})))

        return crumbs


class DownloadView(View):
    """Downloading files."""

    def get(self, request, filetype, project_slug,
            contractor_slug, filename):
        project = get_object_or_404(Project, slug=project_slug)
        if contractor_slug == 'x':
            contractor = None
        else:
            contractor = get_object_or_404(Contractor, slug=contractor_slug)

        if not has_access(request.user, project, contractor):
            return HttpResponseForbidden()

        if filetype == 'reports':
            directory = directories.reports_dir(project, contractor)
        elif filetype == 'results':
            directory = directories.reports_dir(project, contractor)
        elif filetype == 'locations':
            directory = directories.location_shapefile_dir(project, contractor)
        elif filetype == 'organization':
            directory = directories.organization_files_dir(
                project.organization)
        else:
            return HttpResponseForbidden()

        path = os.path.join(directory, filename)

        if not os.path.exists(path):
            raise http.Http404()

        return serve(request, path, '/')


def start_export_run_view(request, project_slug, export_run_id):
    if request.method != "POST":
        logger.debug("method is not POST, but {0}".format(request.method))
        return HttpResponseForbidden()

    try:
        export_run = models.ExportRun.objects.get(pk=export_run_id)
    except models.ExportRun.DoesNotExist:
        logger.debug("No such export run")
        return HttpResponseForbidden()

    if export_run.project.slug != project_slug:
        logger.debug("Wrong project slug")
        return HttpResponseForbidden()

    if not models.has_access(
        request.user, export_run.project, export_run.contractor):
        logger.debug("No access")
        return HttpResponseForbidden()

    # Clear existing export
    export_run.clear()
    export_run.export_running = True
    export_run.save()

    # Start the Celery task
    tasks.start_export_run.delay(export_run.id, request.user)

    return HttpResponse()


def protected_download_export_run(request, project_slug, export_run_id):
    """
    Copied from views.protected_file_download, see there.
    No Apache support, only Nginx.
    """

    try:
        export_run = models.ExportRun.objects.get(pk=export_run_id)
    except models.ExportRun.DoesNotExist:
        return HttpResponseForbidden()

    if export_run.project.slug != project_slug:
        return HttpResponseForbidden()

    if not has_access(request.user, export_run.project, export_run.contractor):
        return HttpResponseForbidden()

    file_path = export_run.file_path
    logger.debug("File path: " + file_path)

    nginx_path = '/'.join([
            '/protected', 'export',
            export_run.project.organization.name,
            os.path.basename(file_path)])

    # This is where the magic takes place.
    response = HttpResponse()
    response['X-Accel-Redirect'] = nginx_path  # Nginx

    # Unset the Content-Type as to allow for the webserver
    # to determine it.
    response['Content-Type'] = ''

    # Only works for Apache and Nginx, under Linux right now
    if settings.DEBUG or not platform.system() == 'Linux':
        return serve(request, file_path, '/')
    return response
