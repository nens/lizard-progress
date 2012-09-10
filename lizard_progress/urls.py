# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.txt.

from django.conf.urls.defaults import patterns, url
from django.contrib import admin
from django.contrib.auth.decorators import login_required

from lizard_map.views import AppView
from lizard_progress.views import ComparisonPopupView
from lizard_progress.views import ComparisonView
from lizard_progress.views import DashboardAreaView
from lizard_progress.views import DashboardCsvView
from lizard_progress.views import DashboardView
from lizard_progress.views import DownloadHomeView
from lizard_progress.views import DownloadReportsView
from lizard_progress.views import MapView
from lizard_progress.views import UploadDialogView
from lizard_progress.views import UploadHomeView
from lizard_progress.views import UploadMeasurementsView
from lizard_progress.views import UploadReportsView
from lizard_progress.views import UploadShapefilesView
from lizard_progress.views import View
from lizard_progress.views import dashboard_graph
from lizard_progress.views import protected_file_download

from lizard_progress.views import ProjectsView
from lizard_progress.views import (
    ProjectWizard, ContractorWizard,
    ActivitiesWizard, HydrovakkenWizard)
from lizard_progress.forms import (
    ProjectForm, MeasurementTypeForm, ShapefileForm)
from lizard_progress.forms import ContractorForm, ExistingUserForm, NewUserForm
from lizard_progress.forms import ProjectChoiceForm, ContractorChoiceForm
from lizard_progress.forms import existing_user_condition, new_user_condition
from lizard_progress.forms import needs_shapefile_condition

from lizard_ui.urls import debugmode_urlpatterns

admin.autodiscover()

urlpatterns = patterns(
    '',
    ## Start N0032 experiments:
    url('^projects/$',
        login_required(ProjectsView.as_view()),
        name='lizard_progress_projecten'),
    url('^admin/$',
        login_required(AppView.as_view(template_name='lizard_progress/admin.html')),
        name='lizard_progress_admin'),
    url('^admin/projects/new/$',
        login_required(ProjectWizard.as_view([ProjectForm])),
        name='lizard_progress_newproject'),
    url('^admin/contractors/new/$',
        login_required(ContractorWizard.as_view(
            [ContractorForm, ExistingUserForm, NewUserForm],
        condition_dict={
                '1': existing_user_condition,
                '2': new_user_condition})),
        name='lizard_progress_newcontractor'),
    url('^admin/activities/new/$',
        login_required(ActivitiesWizard.as_view(
            [ProjectChoiceForm, ContractorChoiceForm,
             MeasurementTypeForm, ShapefileForm],
            condition_dict={
                '3': needs_shapefile_condition})),
        name='lizard_progress_newactivities'),
    url('^admin/hydrovakken/new/$',
        login_required(HydrovakkenWizard.as_view(
            [ProjectChoiceForm, ShapefileForm])),
        name='lizard_progress_newhydrovakken'),
    ## End N0032 experiments.
    url('^projects/(?P<project_slug>[^/]+)/$', login_required(View.as_view()),
        name='lizard_progress_view'),
    url('^projects/(?P<project_slug>[^/]+)/map/$',
        login_required(MapView.as_view()),
        name='lizard_progress_mapview'),
    url('^projects/(?P<project_slug>[^/]+)/comparison/$',
        login_required(ComparisonView.as_view()),
        name='lizard_progress_comparisonview'),
    url('^(?P<project_slug>[^/]+)/comparison/(?P<mtype_slug>[^/]+)/$',
        login_required(ComparisonView.as_view()),
        name='lizard_progress_comparisonview2'),
    url('^(?P<project_slug>[^/]+)/comparison/popup/'
        '(?P<mtype_slug>[^/]+)/(?P<location_code>[^/]+)/$',
        login_required(ComparisonPopupView.as_view()),
        name='lizard_progress_comparisonpopup'),
    url('^projects/(?P<project_slug>[^/]+)/dashboard/$',
        login_required(DashboardView.as_view()),
        name='lizard_progress_dashboardview'),
    url('^dashboardcsv/(?P<project_slug>[^/]+)/(?P<contractor_slug>[^/]+)/$',
        login_required(DashboardCsvView.as_view()),
        name='lizard_progress_dashboardcsvview'),
    url('^upload/$',
        login_required(UploadDialogView.as_view()),
        name='lizard_progress_uploaddialogview'),
    url('^projects/(?P<project_slug>[^/]+)/upload/$',
        login_required(UploadHomeView.as_view()),
        name='lizard_progress_uploadhomeview'),
    url('^projects/(?P<project_slug>[^/]+)/upload/measurements/$',
        login_required(UploadMeasurementsView.as_view()),
        name='lizard_progress_uploadmeasurementsview'),
    url('^projects/(?P<project_slug>[^/]+)/upload/reports/$',
        login_required(UploadReportsView.as_view()),
        name='lizard_progress_uploadreportsview'),
    url('^projects/(?P<project_slug>[^/]+)/upload/shapefiles/$',
        login_required(UploadShapefilesView.as_view()),
        name='lizard_progress_uploadshapefilesview'),
    url('^projects/(?P<project_slug>[^/]+)/download/$',
        login_required(DownloadHomeView.as_view()),
        name='lizard_progress_downloadhomeview'),
    url('^projects/(?P<project_slug>[^/]+)/(?P<contractor_slug>[^/]+)/reports/(?P<report>[^/]+)/$',
        login_required(DownloadReportsView.as_view()),
        name='lizard_progress_downloadreportsview'),
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
