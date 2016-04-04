# (c) Nelen & Schuurmans. GPL licensed, see LICENSE.txt.

"""Views concerned with uploading files."""

import datetime
import json
import logging
import os
import shutil
import tempfile

from django.conf import settings
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.http import Http404
from django.http import HttpResponse
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView

from lizard_ui.views import ViewContextMixin

from lizard_progress import configuration
from lizard_progress import forms
from lizard_progress import tasks
from lizard_progress import models
from lizard_progress.util import directories
from lizard_progress.views.views import ProjectsView
from lizard_progress.views.activity import ActivityView

APP_LABEL = models.Project._meta.app_label

logger = logging.getLogger(__name__)


def json_response(obj):
    """Return a HttpResponse with obj serialized as JSON as content"""
    return HttpResponse(json.dumps(obj), mimetype="application/json")


def remove_uploaded_file_view(request, **kwargs):
    user = request.user
    organization = models.Organization.get_by_user(user)

    if not organization:
        raise PermissionDenied()

    project_slug = kwargs.get('project_slug')
    try:
        project = models.Project.objects.get(slug=project_slug)
    except models.project.DoesNotExist:
        raise Http404()

    uploaded_file_id = kwargs.get('uploaded_file_id')
    uploaded_file = models.UploadedFile.objects.select_related(
        'activity', 'activity__project', 'activity__contractor').get(
        pk=uploaded_file_id)

    if (uploaded_file.activity.contractor != organization
            or uploaded_file.activity.project != project):
        raise PermissionDenied()

    uploaded_file.delete_self()

    if request.method == 'POST':
        return HttpResponse("Uploaded file deleted.")
    else:
        return HttpResponseRedirect(
            reverse('lizard_progress_uploadhomeview',
                    kwargs={'project_slug': project_slug,
                            'activity_id': uploaded_file.activity_id}))


class DummyException(BaseException):
    "Only used for triggering transaction fail"
    pass


class UploadDialogView(TemplateView):
    """File upload dialog."""
    template_name = "lizard_progress/upload.html"


class UploadView(ActivityView):
    def post(self, request, *args, **kwargs):
        """Handle file upload.

        HTTP 200 (OK) is returned, even if processing fails. Not very RESTful,
        but the only way to show custom error messages when using Plupload.

        If we have the whole file (chunk == chunks-1), then process it.
        """

        # Note that the whole chunking thing is currently turned off
        # in Javascript because it is buggy.

        # Usually we return JSON, but not with the simple upload form (for IE)
        return_json = not request.POST.get("simple-upload")

        if not self.activity.can_upload(request.user):
            raise PermissionDenied()

        uploaded_file = request.FILES['file']
        filename = request.POST.get('filename', uploaded_file.name)
        chunk = int(request.POST.get('chunk', 0))
        chunks = int(request.POST.get('chunks', 1))

        # Create a temp dir in which our file definitely doesn't exist yet
        basedir = os.path.join(
            settings.BUILDOUT_DIR, 'var', 'lizard_progress', 'uploaded_files')
        if not os.path.exists(basedir):
            os.makedirs(basedir)
        tmpdir = tempfile.mkdtemp(dir=basedir)

        path = os.path.join(tmpdir, filename)

        with open(path, 'wb' if chunk == 0 else 'ab') as f:
            for chunk_bytes in uploaded_file.chunks():
                f.write(chunk_bytes)

        if chunk == chunks - 1:
            # We have the whole file.
            if return_json:
                return self.process_file(path)
            else:
                self.process_file(path)
                return HttpResponseRedirect(self.url)
        else:
            if return_json:
                return json_response({})
            else:
                return HttpResponseRedirect(self.url)

    def process_file(self, path):
        raise NotImplementedError

    @property
    def url(self):
        return reverse(
            'lizard_progress_uploadhomeview',
            kwargs={'project_slug': self.project_slug,
                    'activity_id': self.activity_id})


class UploadMeasurementsView(UploadView):
    def process_file(self, path):
        uploaded_file = models.UploadedFile.objects.create(
            activity=self.activity,
            uploaded_by=self.user,
            uploaded_at=datetime.datetime.now(),
            rel_file_path=path)

        uploaded_file.schedule_processing()

        return json_response({})


class UploadReportsView(UploadView):
    exts = [".pdf", ".doc", ".zip"]

    def process_file(self, path):

        ext = os.path.splitext(path)[1].lower()
        if not ext in self.exts:
            msg = "Allowed file types: %s." % self.exts
            return json_response({'error': {'details': msg}})

        # The destination directory.
        dst = directories.abs_reports_dir(self.activity)

        # Copy the report.
        shutil.copy(path, dst)

        return json_response({})


class UploadShapefilesView(UploadView):
    exts = [".dbf", ".prj", ".sbn", ".sbx", ".shp", ".shx", ".xml"]

    def process_file(self, path):
        ext = os.path.splitext(path)[1].lower()
        if not ext in self.exts:
            msg = "Allowed file types: %s." % self.exts
            return json_response({'error': {'details': msg}})

        # TODO: perform a sanity check before copying
        # the shapefile to its permanent location?

        # The destination directory.
        dst = directories.abs_shapefile_dir(self.activity)

        # Copy the report.
        shutil.copy(path, dst)

        return json_response({})


class UploadedFileErrorsView(ViewContextMixin, TemplateView):
    template_name = 'lizard_progress/uploaded_file_error_page.html'

    MAX_GOOD_LINES = 2000

    def get(self, request, uploaded_file_id, project_slug, activity_id):
        self.uploaded_file = models.UploadedFile.objects.get(
            pk=uploaded_file_id)
        if self.uploaded_file.uploaded_by != request.user:
            raise PermissionDenied()

        self.user = request.user

        self.errors = self._errors()
        self.general_errors = self._general_errors()
        self.lines_and_errors = self._lines_and_errors()

        return super(UploadedFileErrorsView, self).get(request)

    def _errors(self):
        return models.UploadedFileError.objects.filter(
            uploaded_file=self.uploaded_file).order_by('line')

    def _general_errors(self):
        """Return the errors that have line number 0."""
        return [error.error_message
                for error in self.errors if error.line == 0]

    def _lines_and_errors(self):
        """Return a line-for-line of the file, with errors.

        Each line is a dictionary:
        - 'line_number' (1, ...)
        - 'has_error' (boolean)
        - 'file_line' (string)
        - 'errors' (list of strings)
        """

        errordict = dict()
        for error in self.errors:
            if error.line > 0:
                errordict.setdefault(error.line, []).append(
                    error.error_message)

        lines = []
        abs_path = self.uploaded_file.abs_file_path
        good_lines = 0
        if errordict and os.path.exists(abs_path):
            for line_minus_one, line in enumerate(open(abs_path)):
                line_number = line_minus_one + 1
                if line_number not in errordict:
                    # For speed reasons, if the file is really big,
                    # we only send a max number of the lines without
                    # errors.
                    if good_lines >= self.MAX_GOOD_LINES:
                        continue
                    good_lines += 1

                lines.append({
                    'line_number': line_number,
                    'has_error': line_number in errordict,
                    'file_line': line.strip(),
                    'errors': errordict.get(line_number)})

        return lines


class UploadOrganizationFileView(ProjectsView):
    @models.UserRole.check(models.UserRole.ROLE_MANAGER)
    def post(self, request):
        organization = models.Organization.get_by_user(request.user)

        uploaded_file = request.FILES['file']
        filename = request.POST.get('filename', uploaded_file.name)

        with open(os.path.join(
                directories.abs_organization_files_dir(organization),
                filename), "wb") as f:
            for chunk in uploaded_file.chunks():
                f.write(chunk)

        # Put shapefile parts into zip files
        tasks.shapefile_vacuum.delay(
            directories.abs_organization_files_dir(organization))

        return json_response({})


class UploadProjectFileView(ProjectsView):
    @models.UserRole.check(models.UserRole.ROLE_MANAGER)
    def post(self, request, project_slug):
        project = get_object_or_404(models.Project, slug=project_slug)

        uploaded_file = request.FILES['file']
        filename = request.POST.get('filename', uploaded_file.name)

        with open(os.path.join(
                directories.abs_project_files_dir(project),
                filename), "wb") as f:
            for chunk in uploaded_file.chunks():
                f.write(chunk)

        # Put shapefile parts into zip files
        tasks.shapefile_vacuum.delay(directories.abs_project_files_dir(project))

        return json_response({})


class UploadHydrovakkenView(ProjectsView):
    template_name = "lizard_progress/upload_hydrovakken.html"

    def dispatch(self, request, *args, **kwargs):
        if request.method == 'GET':
            self.form = forms.ShapefileForm()
        elif request.method == 'POST':
            self.form = forms.ShapefileForm(request.POST, request.FILES)

        return super(
            UploadHydrovakkenView, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if not self.form.is_valid():
            return self.get(request, *args, **kwargs)

        if not self.project.is_manager(request.user):
            return HttpResponseForbidden()

        # Remove old files before we move the new ones
        models.Hydrovak.remove_hydrovakken_files(self.project)

        abs_hydrovakken_dir = directories.abs_hydrovakken_dir(self.project)

        # Save uploaded files
        for ext in ['shp', 'dbf', 'shx']:
            uploaded_file = request.FILES[ext]
            with open(
                    os.path.join(abs_hydrovakken_dir, uploaded_file.name),
                    'wb+') as f:
                for chunk in uploaded_file.chunks():
                    f.write(chunk)

        filepath = os.path.join(abs_hydrovakken_dir, request.FILES['shp'].name)

        error_message = models.Hydrovak.reload_from(
            self.project, filepath)

        if error_message:
            messages.add_message(
                request, messages.ERROR, error_message)
            return self.get(request, *args, **kwargs)

        return HttpResponseRedirect(reverse(
            'lizard_progress_downloadhomeview', kwargs={
                'project_slug': self.project.slug}))

    @property
    def hydrovakken_id_field(self):
        return configuration.get(
            activity=None, config_option='hydrovakken_id_field',
            project=self.project)
