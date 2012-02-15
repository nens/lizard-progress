# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.txt.

import logging
import os
import shutil

from matplotlib import figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.db import transaction
from django.http import HttpResponse
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
from lizard_ui.views import ViewContextMixin


logger = logging.getLogger(__name__)


def JsonResponse(ob):
    return HttpResponse(json.dumps(ob),
                        mimetype="application/json")


def document_root():
    return getattr(settings, 'LIZARD_PROGRESS_ROOT',
                   os.path.join(settings.BUILDOUT_DIR, 
                                'var', 
                                'lizard_progress'))


def make_uploaded_file_path(root, project, contractor, mtype, filename):
    return os.path.join(root,
                        project.slug,
                        contractor.slug,
                        mtype.slug,
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
        layers = [{
                'name': '%s %s' % (measurement_type.name, contractor.name),
                'json': ('{"contractor_slug":"%s",' +
                '"measurement_type_slug":"%s",' +
                '"project_slug":"%s"}') %
                (contractor.slug, measurement_type.slug, self.project.slug)
                }
                  for contractor in self.project.contractor_set.all()
                  for measurement_type in
                  self.project.measurementtype_set.all()
                  if has_access(self.request.user, self.project, contractor)]
        logger.debug(layers)
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
        self.project_slug = kwargs.get('project_slug', None)
        self.project = get_object_or_404(Project, slug=self.project_slug)

        if has_access(request.user, self.project):
            return super(UploadView, self).dispatch(request, *args, **kwargs)
        else:
            raise PermissionDenied()

    def upload_url(self):
        return reverse('lizard_progress_uploadview',
                       kwargs={'project_slug': self.project_slug})

    def try_parser(self, parser, path, project, contractor):
        result = {}
        try:
            with transaction.commit_on_success():
                # Call the parser.
                parseresult = parser(path,
                                     project=project,
                                     contractor=contractor)
                
                if parseresult.success:
                    # Success! Move the file.
                    result_dir = os.path.dirname(parseresult.result_path)
                    if not os.path.exists(result_dir):
                        os.makedirs(result_dir)
                    shutil.move(path, parseresult.result_path)
                        
                    return True, {}
                else:
                    # Unsuccess. Were there errors? Then set
                    # them. Note that if there is more than one
                    # parser, there may still be other parsers
                    # after this one that are successful, so we
                    # continue looping.
                    if parseresult.error:
                        result = {'error':
                                      {'details': parseresult.error}}

                    # We raise a dummy exception so that
                    # commit_on_success doesn't commit whatever
                    # was done to our database in the meantime.
                    raise DummyException()
        except DummyException:
            pass

        return False, result

    def post(self, request, *args, **kwargs):
        """Handle file upload.

        HTTP 200 (OK) is returned, even if processing fails. Not very RESTful,
        but the only way to show custom error messages when using Plupload.
        """

        try:
            contractor = Contractor.objects.get(project=self.project,
                                                user=request.user)
        except Contractor.DoesNotExist:
            return JsonResponse({'error': {
                        'details': "User not allowed to upload files."}})

        file = request.FILES['file']
        filename = request.POST['filename']
        chunk = int(request.POST.get('chunk', 0))
        chunks = int(request.POST.get('chunks', 1))
        path = '/tmp/' + filename

        with open(path, 'wb' if chunk == 0 else 'ab') as f:
            for bytes in file.chunks():
                f.write(bytes)

        if chunk == chunks - 1:
            # We have the whole file. Let's find parsers for it and
            # parse it.
            for parser in self.project.specifics().parsers(filename):
                success, errors = self.try_parser(parser, path,
                                                  self.project, contractor)
                if success:
                    break
            else:
                # For loop finishes without breaking.
                if not errors:
                    # No parser was successful, but there were no
                    # errors either.
                    errors = {'error': {'details': "Unknown filetype."}}
            return JsonResponse(errors)
        else:
            return JsonResponse({})


class DashboardAreaView(View):
    template_name = "lizard_progress/dashboard_content.html"

    def dispatch(self, request, *args, **kwargs):
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
    example if you're looking for one. It is for Apache.

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
        # Trickery
        logger.warn("Returned 403 on suspect path %s" % (filename,))

    file_path = make_uploaded_file_path(document_root(), project, contractor,
                                        mtype, filename)
    nginx_path = make_uploaded_file_path('/protected', project, contractor,
                                        mtype, filename)

    if not has_access(request.user, project, contractor):
        logger.warn("Not allowed to access %s", filename)
        return HttpResponseForbidden()

    # This is where the magic takes place.
    response = HttpResponse()
    response['X-Sendfile'] = file_path # Apache
    response['X-Accel-Redirect'] = nginx_path # Nginx

    # Unset the Content-Type as to allow for the webserver
    # to determine it.
    response['Content-Type'] = ''
    # TODO: ... or USE_IIS:...
    if settings.DEBUG or not platform.system() == 'Linux':
        logger.debug(
            "With DEBUG off, we'd serve the programfile via apache: \n%s",
            response)
        return serve(request, file_path, '/')
    logger.debug("Serving programfile %s via apache.", fullpath)
    return response
