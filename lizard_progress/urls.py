# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.txt.
from django.contrib.auth.decorators import login_required
from django.conf.urls.defaults import patterns
from django.conf.urls.defaults import url
from django.contrib import admin

from lizard_ui.urls import debugmode_urlpatterns
from lizard_progress.views import View
from lizard_progress.views import MapView
from lizard_progress.views import UploadView
from lizard_progress.views import DashboardView
from lizard_progress.views import DashboardAreaView
from lizard_progress.views import dashboard_graph
from lizard_progress.views import protected_file_download

admin.autodiscover()

urlpatterns = patterns(
    '',
    url('^(?P<project_slug>[^/]+)/$', login_required(View.as_view()),
        name='lizard_progress_view'),
    url('^(?P<project_slug>[^/]+)/map/$', login_required(MapView.as_view()),
        name='lizard_progress_mapview'),
    url('^(?P<project_slug>[^/]+)/dashboard/$',
        login_required(DashboardView.as_view()),
        name='lizard_progress_dashboardview'),
    url('^(?P<project_slug>[^/]+)/upload/$',
        login_required(UploadView.as_view()),
        name='lizard_progress_uploadview'),
    url('^(?P<project_slug>[^/]+)/dashboard/' +
        '(?P<contractor_slug>[^/]+)/(?P<area_slug>.+)/graph/$',
        dashboard_graph,
        name='lizard_progress_dashboardgraphview'),
    url('^(?P<project_slug>[^/]+)/dashboard/' +
        '(?P<contractor_slug>[^/]+)/(?P<area_slug>.+)/$',
        login_required(DashboardAreaView.as_view()),
        name='lizard_progress_dashboardareaview'),
    url('^file/(?P<project_slug>[^/]+)/' +
        '(?P<contractor_slug>[^/]+)/(?P<measurement_type_slug>[^/]+)/' +
        '(?P<filename>[^/]+)$',
        protected_file_download,
        name='lizard_progress_filedownload'),
    )
urlpatterns += debugmode_urlpatterns()
