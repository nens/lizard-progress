# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.txt.

from django.conf.urls.defaults import patterns, url
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import admin
from django.views.generic import TemplateView

from lizard_map.views import AppView
from lizard_progress.views import View
from lizard_progress.views import MapView
from lizard_progress.views import UploadView
from lizard_progress.views import ComparisonView
from lizard_progress.views import ComparisonPopupView
from lizard_progress.views import DashboardView
from lizard_progress.views import DashboardCsvView
from lizard_progress.views import DashboardAreaView
from lizard_progress.views import dashboard_graph
from lizard_progress.views import protected_file_download

from lizard_progress.forms import ProjectWizard, ProjectForm, MeasurementTypeForm, LocationForm
from lizard_progress.forms import ContractorWizard, ContractorForm, ExistingUserForm, NewUserForm
from lizard_progress.forms import ProjectCreate, ProjectUpdate, ProjectDelete
from lizard_progress.forms import existing_user_condition, new_user_condition

from lizard_ui.urls import debugmode_urlpatterns

admin.autodiscover()

urlpatterns = patterns(
    '',
    ## Start N0032 experiments:
    url('^admin/$', AppView.as_view(template_name='lizard_progress/admin.html')),
    url('^admin/projects/new/$', ProjectWizard.as_view([ProjectForm, LocationForm, MeasurementTypeForm]), name='new_project'),
    url('^project/add/$', ProjectCreate.as_view(), name='project_add'),
    url('^project/(?P<pk>\d+)/$', ProjectUpdate.as_view(), name='project_update'),
    url('^project/(?P<pk>\d+)/delete/$', ProjectDelete.as_view(), name='project_delete'),
    url('^admin/contractors/new/$', ContractorWizard.as_view([ContractorForm, ExistingUserForm, NewUserForm],
        condition_dict={'1': existing_user_condition, '2': new_user_condition}), name='new_contractor'),
    ## End N0032 experiments.
    url('^(?P<project_slug>[^/]+)/$', login_required(View.as_view()),
        name='lizard_progress_view'),
    url('^(?P<project_slug>[^/]+)/map/$', login_required(MapView.as_view()),
        name='lizard_progress_mapview'),
    url('^(?P<project_slug>[^/]+)/comparison/$',
        login_required(ComparisonView.as_view()),
        name='lizard_progress_comparisonview'),
    url('^(?P<project_slug>[^/]+)/comparison/(?P<mtype_slug>[^/]+)/$',
        login_required(ComparisonView.as_view()),
        name='lizard_progress_comparisonview2'),
    url('^(?P<project_slug>[^/]+)/comparison/popup/'
        '(?P<mtype_slug>[^/]+)/(?P<location_unique_id>[^/]+)/$',
        login_required(ComparisonPopupView.as_view()),
        name='lizard_progress_comparisonpopup'),
    url('^(?P<project_slug>[^/]+)/dashboard/$',
        login_required(DashboardView.as_view()),
        name='lizard_progress_dashboardview'),
    url('^dashboardcsv/(?P<project_slug>[^/]+)/(?P<contractor_slug>[^/]+)/$',
        login_required(DashboardCsvView.as_view()),
        name='lizard_progress_dashboardcsvview'),
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
