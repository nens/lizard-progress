# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

# Python 3 is coming
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from django.conf.urls.defaults import include
from django.conf.urls.defaults import patterns, url
from django.contrib import admin
from django.contrib.auth.decorators import login_required

from lizard_progress import forms

from lizard_progress.views import ActivitiesWizard
from lizard_progress.views import ComparisonPopupView
from lizard_progress.views import ComparisonView
from lizard_progress.views import ContractorWizard
from lizard_progress.views import DashboardAreaView
from lizard_progress.views import DashboardCsvView
from lizard_progress.views import DashboardView
from lizard_progress.views import DownloadHomeView
from lizard_progress.views import DownloadView
from lizard_progress.views import DownloadDocumentsView
from lizard_progress.views import DownloadOrganizationDocumentView
from lizard_progress.views import HydrovakkenWizard
from lizard_progress.views import MapView
from lizard_progress.views import ProjectsView
from lizard_progress.views import ResultsWizard
from lizard_progress.views import UploadDialogView
from lizard_progress.views import UploadHomeView
from lizard_progress.views import UploadMeasurementsView
from lizard_progress.views import UploadReportsView
from lizard_progress.views import UploadShapefilesView
from lizard_progress.views import UploadedFileErrorsView
from lizard_progress.views import dashboard_graph
from lizard_progress.views import protected_file_download

from lizard_progress import views
from lizard_progress.views import organization_admin

from lizard_ui.urls import debugmode_urlpatterns

admin.autodiscover()

urlpatterns = patterns(
    '',
    # Homepage
    url('^$',
        login_required(ProjectsView.as_view()),
        name='lizard_progress_projecten'),

    # Change requests are in a subapp
    url(r'^projects/(?P<project_slug>[^/]+)/changerequests/',
        include('lizard_progress.changerequests.urls')),

    # "Projects" page is basically same as homepage
    url('^projects/$',
        login_required(ProjectsView.as_view()),
        name='lizard_progress_projecten'),

    url('^newproject/$',
        login_required(views.NewProjectView.as_view()),
        name='lizard_progress_newproject'),

    url('^archive/$',
        login_required(views.ArchiveProjectsOverview.as_view()),
        name='lizard_progress_archive_overview'),
    url('^archive/(?P<project_slug>[^/]+)$',
        login_required(views.ArchiveProjectsView.as_view()),
        name='lizard_progress_archive'),

    # Admin pages
    url('^admin/$',
        login_required(
            views.View.as_view(template_name='lizard_progress/admin.html')),
        name='lizard_progress_admin'),
    url('^admin/contractors/new/$',
        login_required(ContractorWizard.as_view(
            [forms.ContractorForm])),
        name='lizard_progress_newcontractor'),
    url('^admin/activities/new/$',
        login_required(ActivitiesWizard.as_view(
            [forms.ProjectChoiceForm, forms.ContractorChoiceForm,
             forms.MeasurementTypeForm, forms.ShapefileForm],
            condition_dict={
                '3': forms.needs_shapefile_condition})),
        name='lizard_progress_newactivities'),
    url('^admin/hydrovakken/new/$',
        login_required(HydrovakkenWizard.as_view(
            [forms.ProjectChoiceForm, forms.ShapefileForm])),
        name='lizard_progress_newhydrovakken'),
    url('^admin/results/$',
        login_required(ResultsWizard.as_view(
            [forms.ProjectChoiceForm, forms.ContractorChoiceForm,
             forms.CalculateForm])),
        name='lizard_progress_results'),

    url('^admin/organization/errorconfiguration/$',
        login_required(organization_admin.OrganizationAdminConfiguration.as_view()),
        name='lizard_progress_admin_organization_errorconfiguration'),

    # Organization documents
    url('^projects/documents/download/$',
        login_required(DownloadDocumentsView.as_view()),
        name='lizard_progress_documents_download'),
    url('^download/organization/(?P<organization_id>\d+)/(?P<filename>[^/]+)',
        login_required(DownloadOrganizationDocumentView.as_view()),
        name='lizard_progress_download_organization_document'),

    # Project page per project
    url('^projects/(?P<project_slug>[^/]+)/$',
        login_required(ProjectsView.as_view()),
        name='lizard_progress_view'),
    # Kaartlagen view
    url('^projects/(?P<project_slug>[^/]+)/map/$',
        login_required(MapView.as_view()),
        name='lizard_progress_mapview'),

    # Comparison view -- old hack that can probably be removed
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

    # Dashboard page
    url('^projects/(?P<project_slug>[^/]+)/dashboard/$',
        login_required(DashboardView.as_view()),
        name='lizard_progress_dashboardview'),

    url('^projects/(?P<project_slug>[^/]+)/(?P<contractor_slug>[^/]+)/planning/$',
        login_required(views.PlanningView.as_view()),
        name='lizard_progress_planningview'),

    # Edit contractors and measurement types
    url('^projects/(?P<project_slug>[^/]+)/edit_contractors/$',
        login_required(views.EditContractorsMeasurementTypes.as_view()),
        name='lizard_progress_edit_contractors'),

    # CSV file generation
    url('^dashboardcsv/(?P<project_slug>[^/]+)/(?P<contractor_slug>[^/]+)/$',
        login_required(DashboardCsvView.as_view()),
        name='lizard_progress_dashboardcsvview'),

    # This is where uploads happen
    url('^upload/$',
        login_required(UploadDialogView.as_view()),
        name='lizard_progress_uploaddialogview'),
    # The upload page
    url('^projects/(?P<project_slug>[^/]+)/upload/$',
        login_required(UploadHomeView.as_view()),
        name='lizard_progress_uploadhomeview'),

    # API for the tables that refresh when processing uploaded files
    url('^projects/(?P<project_slug>[^/]+)/upload/uploaded_files/$',
        login_required(views.UploadedFilesView.as_view()),
        name='lizard_progress_uploaded_files_api'),
    # Remove an uploaded file
    url('^projects/(?P<project_slug>[^/]+)/upload/remove_uploaded_file/(?P<uploaded_file_id>\d+)/$',
        login_required(views.remove_uploaded_file_view),
        name='lizard_progress_remove_uploaded_file'),
    # Various uploads
    url('^projects/(?P<project_slug>[^/]+)/upload/measurements/$',
        login_required(UploadMeasurementsView.as_view()),
        name='lizard_progress_uploadmeasurementsview'),
    url('^projects/(?P<project_slug>[^/]+)/upload/reports/$',
        login_required(UploadReportsView.as_view()),
        name='lizard_progress_uploadreportsview'),
    url('^projects/(?P<project_slug>[^/]+)/upload/shapefiles/$',
        login_required(UploadShapefilesView.as_view()),
        name='lizard_progress_uploadshapefilesview'),

    # Download page
    url('^projects/(?P<project_slug>[^/]+)/download/$',
        login_required(DownloadHomeView.as_view()),
        name='lizard_progress_downloadhomeview'),
    url('^download/(?P<filetype>[^/]+)/(?P<project_slug>[^/]+)/' +
        '(?P<contractor_slug>[^/]+)/(?P<filename>[^/]+)',
        login_required(DownloadView.as_view()),
        name='lizard_progress_downloadview'),
    url('^organization_file_upload/$',
        login_required(views.UploadOrganizationFileView.as_view()),
        name='lizard_progress_upload_orgfile'),
    url('^project_file_upload/(?P<project_slug>[^/]+)/$',
        login_required(views.UploadProjectFileView.as_view()),
        name='lizard_progress_upload_projectfile'),
    url('^projects/(?P<project_slug>[^/]+)/hydrovakken_upload/$',
        login_required(views.UploadHydrovakkenView.as_view()),
        name='lizard_progress_upload_hydrovakken'),

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

    # Error messages view
    url('^errors/(?P<uploaded_file_id>\d+)/$',
        login_required(UploadedFileErrorsView.as_view()),
        name='lizard_progress_uploaded_file_error_view'),

    # Start an export run
  url('^projects/(?P<project_slug>[^/]+)/export_run/(?P<export_run_id>[\d]+)/$',
        login_required(views.start_export_run_view),
        name="lizard_progress_start_export_run_view"),
  url('^projects/(?P<project_slug>[^/]+)/export_run/(?P<export_run_id>[\d]+)/download/',
        login_required(views.protected_download_export_run),
        name="lizard_progress_download_export_run_view"),

    # Configuration
    url('^projects/(?P<project_slug>[^/]+)/config/$',
        login_required(views.ConfigurationView.as_view()),
        name="lizard_progress_project_configuration_view"),

    url('^projects/(?P<project_slug>[^/]+)/config/$',
        login_required(views.ConfigurationView.as_view()),
        name="lizard_progress_project_configuration_post"),

    # User management
    url('users/$', login_required(views.UserManagementView.as_view()),
        name="lizard_progress_user_management"),
    url('users/(?P<user_id>\d+)/$',
        login_required(views.SingleUserManagementView.as_view()),
        name="lizard_progress_single_user_management"),
    url('users/newuser/$',
        login_required(views.NewUserManagementView.as_view()),
        name="lizard_progress_new_user_management"),

)

urlpatterns += debugmode_urlpatterns()
