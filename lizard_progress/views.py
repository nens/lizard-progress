# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.txt.

import logging
import os
import platform
import shutil
import time

from matplotlib import figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas

from PIL import Image

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.db import transaction
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.utils import simplejson as json
from django.views.generic import TemplateView
from django.views.static import serve

from lizard_map.matplotlib_settings import SCREEN_DPI
from lizard_map.views import AppView
from lizard_progress.models import has_access
from lizard_progress.models import Area
from lizard_progress.models import Contractor
from lizard_progress.models import Project
from lizard_progress.models import MeasurementType
from lizard_progress.models import ScheduledMeasurement
from lizard_progress.specifics import ProgressParser
from lizard_ui.views import ViewContextMixin


logger = logging.getLogger(__name__)


def JsonResponse(ob):
    return HttpResponse(json.dumps(ob),
                        mimetype="application/json")


def document_root():
    """Get the document root for uploaded files as an absolute path.
    If LIZARD_PROGRESS_ROOT is given in settings, return that,
    otherwise the directory var/lizard_progress/ under BUILDOUT_DIR.
    """

    root = getattr(settings, 'LIZARD_PROGRESS_ROOT', None)
    if root is None:
        root = os.path.join(settings.BUILDOUT_DIR,
                            'var', 'lizard_progress')
    return root


def make_uploaded_file_path(root, project, contractor,
                            measurement_type, filename):
    """Gives the path to some uploaded file, which depends on the
    project it is for, the contractor that uploaded it and the
    measurement type that got its data from this file.

    Project, contractor, measurement_type can each be either a
    model instance of that type or a string containing the slug
    of one.

    Can be used both for absolute file paths (pass in document_root()
    as root) or for URLs that will be passed to Nginx for X-Sendfile
    (uses /protected/ as the root).

    External URLs should use a reverse() call to the
    lizard_progress_filedownload view instead of this function."""

    if isinstance(project, Project):
        project = project.slug
    if isinstance(contractor, Contractor):
        contractor = contractor.slug
    if isinstance(measurement_type, MeasurementType):
        measurement_type = measurement_type.slug

    return os.path.join(root,
                        project,
                        contractor,
                        measurement_type,
                        os.path.basename(filename))


class View(AppView):
    project_slug = None
    project = None
    template_name = 'lizard_progress/home.html'

    def dispatch(self, request, *args, **kwargs):
        self.project_slug = kwargs.get('project_slug', None)
        self.project = get_object_or_404(Project, slug=self.project_slug)

        if has_access(request.user, self.project):
            return super(View, self).dispatch(request, *args, **kwargs)
        else:
            raise PermissionDenied()

    def upload_url(self):
        return reverse('lizard_progress_uploadview',
                       kwargs={'project_slug': self.project_slug})

    def dashboard_url(self):
        return reverse('lizard_progress_dashboardview',
                       kwargs={'project_slug': self.project_slug})

    def map_url(self):
        return reverse('lizard_progress_mapview',
                       kwargs={'project_slug': self.project_slug})


class MapView(View):
    template_name = 'lizard_progress/map.html'

    def crumbs(self):
        crumbs = super(MapView, self).crumbs()

        crumbs.append({
                'url': self.map_url(),
                'description': 'Kaartlagen',
                'title': '%s kaartlagen' % (self.project.name,)
                })

        return crumbs

    def available_layers(self):
        logger.debug("Available layers:")
        layers = []
        for contractor in self.project.contractor_set.all():
            if has_access(self.request.user, self.project, contractor):
                layers.append({
                        'name': '%s %s Alle metingen'
                        % (self.project.name, contractor.name),
                        'json': json.dumps({
                                "contractor_slug":
                                    contractor.slug,
                                "project_slug":
                                    self.project.slug})
                        })
                for measurement_type in self.project.measurementtype_set.all():
                    layers.append({
                            'name': '%s %s %s' %
                            (self.project.name,
                             contractor.name,
                             measurement_type.name),
                            'json': json.dumps({
                                    "contractor_slug":
                                    contractor.slug,
                                    "measurement_type_slug":
                                        measurement_type.slug,
                                    "project_slug":
                                        self.project.slug}),
                            })
        return layers


class DashboardView(View):
    template_name = 'lizard_progress/dashboard.html'

    def crumbs(self):
        crumbs = super(DashboardView, self).crumbs()

        crumbs.append({
                'url': self.dashboard_url(),
                'description': 'Dashboard',
                'title': '%s dashboard' % (self.project.name,)
                })

        return crumbs

    def areas(self):
        areas = []
        for contractor in Contractor.objects.filter(project=self.project):
            if has_access(self.request.user, self.project, contractor):
                for area in Area.objects.filter(project=self.project):
                    areas.append((contractor, area,
                                  reverse('lizard_progress_dashboardareaview',
                                          kwargs={
                                    'contractor_slug': contractor.slug,
                                    'project_slug': self.project.slug,
                                    'area_slug': area.slug})))

        return areas


class DummyException(BaseException):
    "Only used for triggering transaction fail"
    pass


class UploadView(ViewContextMixin, TemplateView):
    template_name = "lizard_progress/upload.html"

    def dispatch(self, request, *args, **kwargs):
        """Find project and contractor objects. A successful upload
        can only be performed by a contractor for some specific
        project.  Check if user has access to this project, and if he
        can upload files."""

        self.project_slug = kwargs.get('project_slug', None)
        self.project = get_object_or_404(Project, slug=self.project_slug)

        if not has_access(request.user, self.project):
            return HttpResponseForbidden()

        return super(UploadView, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        """Handle file upload.

        HTTP 200 (OK) is returned, even if processing fails. Not very RESTful,
        but the only way to show custom error messages when using Plupload.

        If we have the whole file (chunk == chunks-1), then process it.
        """

        try:
            self.contractor = Contractor.objects.get(project=self.project,
                                                     user=request.user)
        except Contractor.DoesNotExist:
            return JsonResponse({'error': {
                        'details': "User not allowed to upload files."}})

        file = request.FILES['file']
        filename = request.POST['filename']
        chunk = int(request.POST.get('chunk', 0))
        chunks = int(request.POST.get('chunks', 1))
        path = os.path.join('/tmp', filename)

        with open(path, 'wb' if chunk == 0 else 'ab') as f:
            for bytes in file.chunks():
                f.write(bytes)

        if chunk == chunks - 1:
            # We have the whole file.
            return self.process_file(path)
        else:
            return JsonResponse({})

    def process_file(self, path):
        """Find parsers for the uploaded file and see if they accept it."""

        filename = os.path.basename(path)

        for parser in self.project.specifics().parsers(filename):
            # Try_parser takes care of moving the file to its correct
            # destination if successful, and all database operations.
            success, errors = self.try_parser(parser, path)

            if success:
                return JsonResponse({})
            if errors:
                return JsonResponse(errors)

        # Found no suitable parsers
        return JsonResponse({'error': {'details': "Unknown filetype."}})

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

                if parseresult.success:
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
        """Actually call the parser. Open and close files. Return result."""

        file_object = self.open_uploaded_file(path)

        parser_instance = parser(self.project,
                                 self.contractor,
                                 file_object)
        parseresult = parser_instance.parse()

        if hasattr(file_object, 'close'):
            file_object.close()

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
            new_filename = ('%s-%d-%s' % (time.strftime('%Y%m%d-%H%M%S'),
                                          seq, orig_filename))
            if not os.path.exists(os.path.join(dirname, new_filename)):
                break
            # Increase sequence number if filename exists
            seq += 1

        return os.path.join(dirname, new_filename)

    def open_uploaded_file(self, path):
        """Open file using PIL.Image.open if it is an image, otherwise
        open normally."""
        filename = os.path.basename(path)

        for ext in ('.jpg', '.gif', '.png'):
            if filename.lower().endswith(ext):
                ob = Image.open(path)
                ob.name = filename
                return ob
        return open(path, "rb")


class DashboardAreaView(View):
    template_name = "lizard_progress/dashboard_content.html"

    def dispatch(self, request, *args, **kwargs):
        """Get objects project, area and contractor from the request,
        404 if they are not found. Check if the user has access."""

        self.project_slug = kwargs.get('project_slug', None)
        self.project = get_object_or_404(Project, slug=self.project_slug)
        self.area_slug = kwargs.get('area_slug', None)
        self.area = get_object_or_404(Area,
                                      project=self.project,
                                      slug=self.area_slug)
        self.contractor_slug = kwargs.get('contractor_slug', None)
        self.contractor = get_object_or_404(Contractor,
                                            project=self.project,
                                            slug=self.contractor_slug)

        if not has_access(request.user, self.project, self.contractor):
            raise PermissionDenied()

        return (super(DashboardAreaView, self).
                dispatch(request, *args, **kwargs))

    def graph_url(self):
        """Url to the actual graph."""
        return reverse('lizard_progress_dashboardgraphview', kwargs={
                'project_slug': self.project.slug,
                'contractor_slug': self.contractor.slug,
                'area_slug': self.area.slug})


class ScreenFigure(figure.Figure):
    """A convenience class for creating matplotlib figures.

    Dimensions are in pixels. Float division is required,
    not integer division!
    """
    def __init__(self, width, height):
        super(ScreenFigure, self).__init__(dpi=SCREEN_DPI)
        self.set_size_pixels(width, height)
        self.set_facecolor('white')

    def set_size_pixels(self, width, height):
        dpi = self.get_dpi()
        self.set_size_inches(width / dpi, height / dpi)


@login_required
def dashboard_graph(request, project_slug, contractor_slug,
                    area_slug, *args, **kwargs):
    """Show the work in progress per area in pie charts.

    A single PNG image is returned as a response.
    """
    project = get_object_or_404(Project, slug=project_slug)
    area = get_object_or_404(Area, project=project, slug=area_slug)
    contractor = get_object_or_404(Contractor, project=project,
                                   slug=contractor_slug)

    if not has_access(request.user, project, contractor):
        raise PermissionDenied()

    fig = ScreenFigure(600, 350)  # in pixels
    fig.text(0.5, 0.85, 'Uitgevoerde werkzaamheden', fontsize=14, ha='center')
    fig.subplots_adjust(left=0.05, right=0.95)  # smaller margins
    y_title = -0.2  # a bit lower

    def autopct(pct):
        "Convert absolute numbers into percentages."
        total = done + todo
        return "%d" % int(round(pct * total / 100.0))

    def subplot_generator(images):
        # Maybe we can make this smarter later on
        rows = 1
        cols = images

        start = 100 * rows + 10 * cols

        n = 0
        while n < images:
            n += 1
            yield start + n

    mtypes = project.measurementtype_set.all()
    subplots = subplot_generator(len(mtypes))

    for mtype in mtypes:
        # Profiles to be measured
        total = (ScheduledMeasurement.objects.
                 filter(project=project,
                        contractor=contractor,
                        measurement_type=mtype,
                        location__area=area).count())

        # Measured profiles
        done = ScheduledMeasurement.objects.filter(project=project,
                                                   contractor=contractor,
                                                   measurement_type=mtype,
                                                   location__area=area,
                                                   complete=True).count()

        todo = total - done
        x = [done, todo]
        labels = ['Wel', 'Niet']
        colors = ['#50CD34', '#FE6535']
        ax = fig.add_subplot(subplots.next())
        ax.pie(x, labels=labels, colors=colors, autopct=autopct)
        ax.set_title(mtype.name, y=y_title)
        ax.set_aspect('equal')  # circle

    # Create the response
    response = HttpResponse(content_type='image/png')
    canvas = FigureCanvas(fig)
    canvas.print_png(response)
    return response


@login_required
def protected_file_download(request, project_slug, contractor_slug,
                                   measurement_type_slug, filename):
    """
    We need our own file_download view because contractors can only see their
    own files, and the URLs of other contractor's files are easy to guess.

    Copied and adapted from deltaportaal, which has a more generic
    example, in case you're looking for one. It is for Apache.

    The one below works for both Apache (untested) and Nginx.  I used
    the docs at http://wiki.nginx.org/XSendfile for the Nginx
    configuration.  Basically, Nginx serves /protected/ from the
    document root at BUILDOUT_DIR+'var', and we x-accel-redirect
    there. Also see the bit of nginx conf in hdsr's etc/nginx.conf.in.
    """

    project = get_object_or_404(Project, slug=project_slug)
    contractor = get_object_or_404(Contractor, slug=contractor_slug,
                                   project=project)
    mtype = get_object_or_404(MeasurementType, slug=measurement_type_slug,
                              project=project)

    logger.debug("Incoming programfile request for %s", filename)

    if '/' in filename or '\\' in filename:
        # Trickery?
        logger.warn("Returned Forbidden on suspect path %s" % (filename,))
        return HttpResponseForbidden()

    if not has_access(request.user, project, contractor):
        logger.warn("Not allowed to access %s", filename)
        return HttpResponseForbidden()

    file_path = make_uploaded_file_path(document_root(), project, contractor,
                                        mtype, filename)
    nginx_path = make_uploaded_file_path('/protected', project, contractor,
                                        mtype, filename)

    # This is where the magic takes place.
    response = HttpResponse()
    response['X-Sendfile'] = file_path  # Apache
    response['X-Accel-Redirect'] = nginx_path  # Nginx

    # Unset the Content-Type as to allow for the webserver
    # to determine it.
    response['Content-Type'] = ''
    # TODO: ... or USE_IIS:...
    if settings.DEBUG or not platform.system() == 'Linux':
        logger.debug(
            "With DEBUG off, we'd serve the programfile via webserver: \n%s",
            response)
        return serve(request, file_path, '/')
    logger.debug("Serving programfile %s via webserver.", file_path)
    return response
