# (c) Nelen & Schuurmans. GPL licensed, see LICENSE.txt.

"""Views concerned with uploading files.

See wizards.py for wizard-specific upload code.
"""

import datetime
import logging
import os
import shutil
import tempfile

from django.conf import settings
from django.contrib import messages
from django.contrib.gis.gdal import DataSource
from django.contrib.gis.geos import LineString
from django.contrib.gis.geos import MultiLineString
from django.contrib.gis.geos import fromstr
from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.http import Http404
from django.http import HttpResponse
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.utils import simplejson as json
from django.views.generic import TemplateView
from django.views.generic import View

from lizard_ui.views import ViewContextMixin
from lizard_ui.layout import Action

from lizard_progress import forms
from lizard_progress import tasks
from lizard_progress import models
from lizard_progress.util import directories
from lizard_progress.views.views import ProjectsView
from lizard_progress import configuration


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

    try:
        contractor = models.Contractor.objects.get(
            project=project,
            organization=organization)
    except models.Contractor.DoesNotExist:
        raise PermissionDenied()

    uploaded_file_id = kwargs.get('uploaded_file_id')
    uploaded_file = models.UploadedFile.objects.get(pk=uploaded_file_id)
    if (uploaded_file.contractor != contractor
        or uploaded_file.project != project):
        raise PermissionDenied()

    uploaded_file.delete_self()

    if request.method == 'POST':
        return HttpResponse("Uploaded file deleted.")
    else:
        return HttpResponseRedirect(
            reverse('lizard_progress_uploadhomeview',
                    kwargs={'project_slug': project_slug}))


class DummyException(BaseException):
    "Only used for triggering transaction fail"
    pass


class UploadDialogView(TemplateView):
    """File upload dialog."""
    template_name = "lizard_progress/upload.html"


class UploadHomeView(ProjectsView):
    """The homepage for uploading files.

    Within a project, there are various files to be uploaded:
    measurements, shapefiles, reports, etc. This view is the
    starting point for a contractor who has to upload data.
    """
    template_name = "lizard_progress/upload_page.html"
    active_menu = "upload"

    def __init__(self, *args, **kwargs):
        super(UploadHomeView, self).__init__(*args, **kwargs)
        self.project_slug = None
        self.project = None

    def get(self, request, *args, **kwargs):
        self.project_slug = kwargs.get('project_slug', None)
        self.project = get_object_or_404(
            models.Project, slug=self.project_slug)

        if not self.project.can_upload(request.user):
            return HttpResponseForbidden()

        try:
            self.contractor = models.Contractor.objects.get(
                project=self.project,
                organization__userprofile__user=request.user)
        except models.Contractor.DoesNotExist:
            self.contractor = None

        if models.has_access(request.user, self.project):
            return super(UploadHomeView, self).get(request, *args, **kwargs)
        else:
            return HttpResponseForbidden()

    @staticmethod
    def upload_dialog_url():
        """Returns URL to the file upload dialog."""
        return reverse('lizard_progress_uploaddialogview')

    def upload_measurements_url(self):
        """Returns URL to post measurements to."""
        return reverse('lizard_progress_uploadmeasurementsview',
                       kwargs={'project_slug': self.project_slug})

    def upload_reports_url(self):
        """Returns URL to post project reports to."""
        return reverse('lizard_progress_uploadreportsview',
                       kwargs={'project_slug': self.project_slug})

    def upload_shapefiles_url(self):
        """Returns URL to post a project's (mother) shapefile to."""
        return reverse('lizard_progress_uploadshapefilesview',
                       kwargs={'project_slug': self.project_slug})

    @property
    def breadcrumbs(self):
        """Breadcrumbs for this page."""
        crumbs = super(UploadHomeView, self).breadcrumbs

        crumbs.append(
            Action(
                description=("Uploads for {project}"
                             .format(project=self.project.name)),
                name="Upload",
                url=reverse(
                    'lizard_progress_uploadhomeview',
                    kwargs={'project_slug': self.project_slug})))

        return crumbs

    def files_ready(self):
        if not self.contractor:
            return []

        if not hasattr(self, '_files_ready'):
            self._files_ready = list(models.UploadedFile.objects.filter(
                    project=self.project,
                    contractor=self.contractor,
                    ready=True))
        return self._files_ready

    def files_not_ready(self):
        if not self.contractor:
            return []

        if not hasattr(self, '_files_not_ready'):
            self._files_not_ready = list(models.UploadedFile.objects.filter(
                    project=self.project,
                    contractor=self.contractor,
                    ready=False))
        return self._files_not_ready


class UploadedFilesView(UploadHomeView):
    """Return uploaded files as a JSON array."""
    def get(self, request, *args, **kwargs):
        self.project_slug = kwargs.get('project_slug', None)
        self.project = get_object_or_404(
            models.Project, slug=self.project_slug)

        if not self.project.can_upload(request.user):
            return HttpResponseForbidden()

        try:
            self.contractor = models.Contractor.objects.get(
                project=self.project,
                organization__userprofile__user=request.user)
        except models.Contractor.DoesNotExist:
            self.contractor = None

        if not models.has_access(request.user, self.project):
            return HttpResponseForbidden()

        if not self.contractor:
            return []

        return HttpResponse(
            json.dumps([
                    uploaded_file.as_dict()
                    for uploaded_file in
                    models.UploadedFile.objects.filter(
                        project=self.project,
                        contractor=self.contractor)]),
            content_type="application/json")


class UploadView(View):

    def dispatch(self, request, *args, **kwargs):
        """Find project and contractor objects. A successful upload
        can only be performed by a contractor for some specific
        project.  Check if user has access to this project, and if he
        can upload files."""

        self.project_slug = kwargs.get('project_slug', None)
        self.project = get_object_or_404(
            models.Project, slug=self.project_slug)

        if not models.has_access(request.user, self.project):
            return HttpResponseForbidden()

        self.user = request.user

        return super(UploadView, self).dispatch(
            request, *args, **kwargs)

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

        try:
            self.contractor = models.Contractor.objects.get(
                project=self.project,
                organization__userprofile__user=request.user)
        except models.Contractor.DoesNotExist:
            if return_json:
                return json_response({'error': {
                            'details': "User not allowed to upload files."}})
            else:
                raise PermissionDenied("User not allowed to upload files.")

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
            kwargs={'project_slug': self.project_slug})


class UploadMeasurementsView(UploadView):
    def process_file(self, path):
        uploaded_file = models.UploadedFile.objects.create(
            project=self.project,
            contractor=self.contractor,
            uploaded_by=self.user,
            uploaded_at=datetime.datetime.now(),
            path=path)
        tasks.process_uploaded_file_task.delay(uploaded_file.id)

        return json_response({})


class UploadReportsView(UploadView):
    exts = [".pdf", ".doc", ".zip"]

    @staticmethod
    def get_directory(contractor):
        return directories.reports_dir(contractor.project, contractor)

    def process_file(self, path):

        ext = os.path.splitext(path)[1].lower()
        if not ext in self.exts:
            msg = "Allowed file types: %s." % self.exts
            return json_response({'error': {'details': msg}})

        # The destination directory.
        dst = UploadReportsView.get_directory(self.contractor)

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
        dst = directories.shapefile_dir(
            self.contractor.project, self.contractor)

        # Copy the report.
        shutil.copy(path, dst)

        return json_response({})


class UploadedFileErrorsView(ViewContextMixin, TemplateView):
    template_name = 'lizard_progress/uploaded_file_error_page.html'

    def get(self, request, uploaded_file_id):
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
        path = self.uploaded_file.path
        if errordict and os.path.exists(path):
            for line_minus_one, line in enumerate(open(path)):
                line_number = line_minus_one + 1
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
                directories.organization_files_dir(organization),
                filename), "wb") as f:
            for chunk in uploaded_file.chunks():
                f.write(chunk)

        return json_response({})


class UploadProjectFileView(ProjectsView):
    @models.UserRole.check(models.UserRole.ROLE_MANAGER)
    def post(self, request, project_slug):
        #organization = models.Organization.get_by_user(request.user)
        project = get_object_or_404(models.Project, slug=project_slug)
        
        uploaded_file = request.FILES['file']
        filename = request.POST.get('filename', uploaded_file.name)

        with open(os.path.join(
                directories.project_files_dir(project),
                filename), "wb") as f:
            for chunk in uploaded_file.chunks():
                f.write(chunk)

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

    @property
    def hydrovakken_id_field(self):
        return configuration.get(
            self.project, 'hydrovakken_id_field')

    def post(self, request, *args, **kwargs):
        if not self.form.is_valid():
            return self.get(request, *args, **kwargs)

        if not self.project.is_manager(request.user):
            return HttpResponseForbidden()

        hydrovakken_dir = directories.hydrovakken_dir(self.project)

        filename = request.FILES['shp'].name

        # Remove old hydrovakken
        for filename in os.listdir(hydrovakken_dir):
            filepath = os.path.join(hydrovakken_dir, filename)
            if os.path.isfile(filepath):
                os.remove(filepath)
        models.Hydrovak.objects.filter(project=self.project).delete()

        # Save uploaded files
        for ext in ['shp', 'dbf', 'shx']:
            uploaded_file = request.FILES[ext]
            with open(
                os.path.join(hydrovakken_dir, uploaded_file.name), 'wb+') as f:
                for chunk in uploaded_file.chunks():
                    f.write(chunk)

        filepath = os.path.join(hydrovakken_dir, request.FILES['shp'].name)
        if isinstance(filepath, unicode):
            filepath = filepath.encode('utf8')
        datasource = DataSource(filepath)

        id_field_name = self.hydrovakken_id_field
        layer = datasource[0]

        for feature in layer:
            if id_field_name in feature.fields:
                # The shape can contain both LineStrings and
                # MultiLineStrings - to be able to save both we
                # convert them all to multis
                geom = fromstr(feature.geom.ewkt)
                if isinstance(geom, LineString):
                    geom = MultiLineString(geom)

                hydrovak, created = models.Hydrovak.objects.get_or_create(
                    project=self.project,
                    br_ident=unicode(feature[id_field_name]),
                    defaults={'the_geom': geom})
                if not created:
                    hydrovak.the_geom = geom
                    hydrovak.save()
            else:
                messages.add_message(
                    request, messages.ERROR,
                    'Veld "{}" niet gevonden in de shapefile. '
                    'Pas de shapefile aan,'
                    'of geef een ander ID veld aan op het Configuratie scherm.'
                    .format(self.hydrovakken_id_field))
                return self.get(request, *args, **kwargs)

        return HttpResponseRedirect(reverse(
                'lizard_progress_downloadhomeview', kwargs={
                    'project_slug': self.project.slug}))
