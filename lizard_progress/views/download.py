# (c) Nelen & Schuurmans. GPL licensed, see LICENSE.txt.

"""Views concerned with downloading files."""

from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.views.generic import View
from lizard_map.views import AppView
from lizard_progress.models import Contractor
from lizard_progress.models import Project
from lizard_progress.models import has_access
from lizard_progress.views.upload import UploadReportsView
import mimetypes
import os


class DownloadHomeView(AppView):
    """This view offers links to downloadable project artifacts.

    If the user does not have sufficient rights,
    a `HttpResponseForbidden` is returned.
    """
    template_name = "lizard_progress/download_home.html"

    def __init__(self, *args, **kwargs):
        super(DownloadHomeView, self).__init__(*args, **kwargs)
        self.project = None
        self.user = None

    def dispatch(self, request, *args, **kwargs):
        self.user = request.user
        project_slug = kwargs.pop('project_slug', None)
        self.project = get_object_or_404(Project, slug=project_slug)
        if not has_access(self.user, self.project):
            return HttpResponseForbidden()
        return super(DownloadHomeView, self).dispatch(request, *args, **kwargs)

    def crumbs(self):
        """Returns a list of breadcrumbs."""
        crumbs = super(DownloadHomeView, self).crumbs()

        crumbs.append({
            'url': reverse('lizard_progress_view',
                kwargs={'project_slug': self.project.slug}),
            'description': self.project.name,
            'title': self.project.name
        })

        crumbs.append({
            'url': reverse('lizard_progress_downloadhomeview',
                kwargs={'project_slug': self.project.slug}),
            'description': 'Download',
            'title': 'Bestanden downloaden'
        })

        return crumbs

    def reports(self):
        """Returns a list of links to project reports.

        Reports the user is not allowed to see are
        excluded from the list.
        """
        if not self.project:
            return []

        reports = []

        for contractor in self.project.contractor_set.all():
            if has_access(self.user, self.project, contractor):
                directory = UploadReportsView.get_directory(contractor)
                if os.path.isdir(directory):
                    for filename in os.listdir(directory):
                        fullname = os.path.join(directory, filename)
                        if os.path.isfile(fullname):
                            ext = os.path.splitext(filename)[1].lower()
                            if ext in UploadReportsView.exts:
                                url = reverse(
                                    'lizard_progress_downloadreportsview',
                                    kwargs={
                                        'project_slug': self.project.slug,
                                        'contractor_slug': contractor.slug,
                                        'report': filename
                                    }
                                )
                                reports.append({
                                    'contractor': contractor.name,
                                    'name': filename,
                                    'url': url
                                })

        return reports


class DownloadReportsView(View):

    def get(self, request, *args, **kwargs):
        """Returns the requested project report.

        Throws a `HttpResponseForbidden` if the user
        is not allowed to view the report.
        """

        project_slug = kwargs.pop('project_slug', None)
        project = get_object_or_404(Project, slug=project_slug)
        contractor_slug = kwargs.pop('contractor_slug', None)
        contractor = get_object_or_404(Contractor,
            project=project, slug=contractor_slug)
        if not has_access(request.user, project, contractor):
            return HttpResponseForbidden()

        filename = os.path.basename(kwargs.pop('report', None))
        ext = os.path.splitext(filename)[1].lower()
        if not ext in UploadReportsView.exts:
            return HttpResponseForbidden()

        directory = UploadReportsView.get_directory(contractor)
        fullname = os.path.join(directory, filename)
        if not os.path.isfile(fullname):
            return HttpResponseForbidden()

        response = HttpResponse(file(fullname).read())
        response['Content-Type'] = mimetypes.guess_type(filename)
        response['Content-Disposition'] = 'attachment; filename=%s' % filename
        return response
