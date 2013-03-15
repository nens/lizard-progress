# (c) Nelen & Schuurmans. GPL licensed, see LICENSE.txt.

"""Views concerned with uploading files.

See wizards.py for wizard-specific upload code.
"""

import datetime
import logging
import os
import shutil
import time

from django.conf import settings
from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpResponseRedirect
from django.http import Http404
from django.http import HttpResponse
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.utils import simplejson as json
from django.views.generic import TemplateView
from django.views.generic import View

from lizard_ui.views import ViewContextMixin
from lizard_progress import specifics
from lizard_progress import tasks
from lizard_progress import models
from lizard_progress.tools import unique_filename
from lizard_progress.views.views import document_root
from lizard_progress.views.views import make_uploaded_file_path
from lizard_progress.views.views import ProjectsView
from lizard_progress.views.views import View as ProgressView


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

    uploaded_file.delete()
    return HttpResponseRedirect(
        reverse('lizard_progress_uploadhomeview',
                kwargs={'project_slug': project_slug}))


class DummyException(BaseException):
    "Only used for triggering transaction fail"
    pass


class UploadDialogView(TemplateView):
    """File upload dialog."""
    template_name = "lizard_progress/upload.html"


class UploadHomeView(ProjectsView, ProgressView):
    """The homepage for uploading files.

    Within a project, there are various files to be uploaded:
    measurements, shapefiles, reports, etc. This view is the
    starting point for a contractor who has to upload data.
    """
    template_name = "lizard_progress/upload_page.html"

    def __init__(self, *args, **kwargs):
        super(UploadHomeView, self).__init__(*args, **kwargs)
        self.project_slug = None
        self.project = None

    def get(self, request, *args, **kwargs):
        self.project_slug = kwargs.get('project_slug', None)
        self.project = get_object_or_404(
            models.Project, slug=self.project_slug)

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

    def crumbs(self):
        """Returns a list of breadcrumbs."""
        crumbs = super(UploadHomeView, self).crumbs()
        crumbs.append({
            'description': self.project.name,
            'url': reverse('lizard_progress_view',
                kwargs={'project_slug': self.project_slug})
        })
        crumbs.append({
            'description': 'Upload',
            'url': reverse('lizard_progress_uploadhomeview',
                kwargs={'project_slug': self.project_slug})
        })
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

        try:
            self.contractor = models.Contractor.objects.get(
                project=self.project,
                organization__userprofile__user=request.user)
        except models.Contractor.DoesNotExist:
            return json_response({'error': {
                        'details': "User not allowed to upload files."}})

        uploaded_file = request.FILES['file']
        filename = request.POST['filename']
        chunk = int(request.POST.get('chunk', 0))
        chunks = int(request.POST.get('chunks', 1))
        path = os.path.join('/tmp', filename)

        with open(path, 'wb' if chunk == 0 else 'ab') as f:
            for chunk_bytes in uploaded_file.chunks():
                f.write(chunk_bytes)

        if chunk == chunks - 1:
            # We have the whole file.
            return self.process_file(path)
        else:
            return json_response({})

    def process_file(self, path):
        raise NotImplementedError


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


class OldUploadMeasurementsView(UploadView):
    """Handles file upload, file validation, entering data into the
    database and moving files to their destination.

    XXX: This will all now be handled by a background Celery task."""

    def process_file(self, path):
        """Find parsers for the uploaded file and see if they accept it."""

        filename = os.path.basename(path)

        for parser in self.project.specifics().parsers(filename):
            # Try_parser takes care of moving the file to its correct
            # destination if successful, and all database operations.
            success, errors = self.try_parser(parser, path)

            if success:
                return json_response({})
            if errors:
                return json_response(errors)

        # Found no suitable parsers
        return json_response({
                'error': {'details': "Unknown filetype or empty file."}})

    def try_parser(self, parser, path):
        """Tries a particular parser. Wraps everything in a database
        transaction so that nothing is changed in the database in case
        of an error message. Moves the file to the current location
        and updates its taken measurements with the new filename in
        case of success."""

        errors = {}

        try:
            with transaction.commit_on_success():
                # Call the parser.
                parseresult = self.call_parser(parser, path)

                if (parseresult.success
                    and hasattr(parseresult, 'measurements')
                    and parseresult.measurements):
                    # Get mtype from the parser result, for use in pathname
                    mtype = (parseresult.measurements[0].
                             scheduled.measurement_type)

                    # Move the file.
                    target_path = self.path_for_uploaded_file(mtype, path)
                    shutil.move(path, target_path)

                    # Update measurements.
                    for m in parseresult.measurements:
                        m.filename = target_path
                        m.save()

                    return True, {}
                elif parseresult.success:
                    # Success, but no results.  Don't count this as
                    # success, so that other parsers may be tried.
                    parseresult.success = False
                    # Prevent database change.
                    raise DummyException()
                else:
                    # Unsuccess. Were there errors? Then set
                    # them.
                    if parseresult.error:
                        errors = {'error':
                                      {'details': parseresult.error}}

                    # We raise a dummy exception so that
                    # commit_on_success doesn't commit whatever
                    # was done to our database in the meantime.
                    raise DummyException()
        except DummyException:
            pass

        return False, errors

    def call_parser(self, parser, path):
        """Actually call the parser. Open files. Return result."""

        parser_instance = specifics.parser_factory(
            parser,
            self.project,
            self.contractor,
            path)
        parseresult = parser_instance.parse()
        return parseresult

    def upload_url(self):
        """Is this used?"""
        return reverse('lizard_progress_uploadview',
                       kwargs={'project_slug': self.project_slug})

    def path_for_uploaded_file(self, measurement_type, uploaded_path):
        """Create dirname based on project etc. Guaranteed not to
        exist yet at the time of checking."""

        dirname = os.path.dirname(make_uploaded_file_path(
                document_root(),
                self.project, self.contractor,
                measurement_type, 'dummy'))

        # Create directory if does not exist yet
        if not os.path.exists(dirname):
            os.makedirs(dirname)

        # Figure out a filename that doesn't exist yet
        orig_filename = os.path.basename(uploaded_path)
        seq = 0
        while True:
            new_filename = unique_filename(orig_filename, seq)
            new_filename = ('%s-%d-%s' % (time.strftime('%Y%m%d-%H%M%S'),
                                          seq, orig_filename))
            if not os.path.exists(os.path.join(dirname, new_filename)):
                break
            # Increase sequence number if filename exists
            seq += 1

        return os.path.join(dirname, new_filename)


class UploadReportsView(UploadView):

    exts = [".pdf"]

    @staticmethod
    def get_directory(contractor):
        return os.path.join(settings.BUILDOUT_DIR, 'var', APP_LABEL,
            contractor.project.slug, contractor.slug, 'reports')

    def process_file(self, path):

        ext = os.path.splitext(path)[1].lower()
        if not ext in self.exts:
            msg = "Allowed file types: %s." % self.exts
            return json_response({'error': {'details': msg}})

        # The destination directory.
        dst = UploadReportsView.get_directory(self.contractor)

        # Create it if necessary.
        if not os.path.exists(dst):
            os.makedirs(dst)

        # Copy the report.
        shutil.copy(path, dst)

        return json_response({})


class UploadShapefilesView(UploadView):

    exts = [".dbf", ".prj", ".sbn", ".sbx", ".shp", ".shx", ".xml"]

    @staticmethod
    def get_directory(contractor):
        return os.path.join(settings.BUILDOUT_DIR, 'var', APP_LABEL,
            contractor.project.slug, contractor.slug, 'shapefile')

    def process_file(self, path):

        ext = os.path.splitext(path)[1].lower()
        if not ext in self.exts:
            msg = "Allowed file types: %s." % self.exts
            return json_response({'error': {'details': msg}})

        # TODO: perform a sanity check before copying
        # the shapefile to its permanent location?

        # The destination directory.
        dst = UploadShapefilesView.get_directory(self.contractor)

        # Create it if necessary.
        if not os.path.exists(dst):
            os.makedirs(dst)

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
