# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

# Python 3 is coming
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from django.conf.urls import include
from django.conf.urls import patterns
from django.conf.urls import url
from django.contrib import admin
from django.contrib.auth.decorators import login_required

from lizard_progress.views import ActivitiesView
from lizard_progress.views import DashboardView
from lizard_progress.views import DashboardCsvView
from lizard_progress.views import DownloadHomeView
from lizard_progress.views import DownloadView
from lizard_progress.views import DownloadDocumentsView
from lizard_progress.views import DownloadOrganizationDocumentView
from lizard_progress.views import InlineMapView
from lizard_progress.views import InlineMapViewNew
from lizard_progress.views import MapView
from lizard_progress.views import ProjectsView
from lizard_progress.views import UploadDialogView
from lizard_progress.views import UploadReportsView
from lizard_progress.views import UploadShapefilesView
from lizard_progress.views import UploadedFileErrorsView
from lizard_progress.views import dashboard_graph

from lizard_progress import views
from lizard_progress.views import organization_admin

from lizard_ui.urls import debugmode_urlpatterns

admin.autodiscover()

activity_urls = [
    # Change requests are in a subapp
    url(r'changerequests/',
        include('lizard_progress.changerequests.urls')),
    # Dashboard graphs
    url('graph/$',
        dashboard_graph,
        name='lizard_progress_dashboardgraphview'),
    # The upload page
    url('upload/$',
        login_required(views.activity.UploadHomeView.as_view()),
        name='lizard_progress_uploadhomeview'),
    # Various uploads
    url('upload/measurement/$',
        login_required(views.upload.UploadMeasurementsView.as_view()),
        name='lizard_progress_uploadmeasurementsview'),
    url('upload/reports/$',
        login_required(UploadReportsView.as_view()),
        name='lizard_progress_uploadreportsview'),
    url('upload/shapefiles/$',
        login_required(UploadShapefilesView.as_view()),
        name='lizard_progress_uploadshapefilesview'),

    # Configuration
    url('config/$',
        login_required(views.activity.ConfigurationView.as_view()),
        name="lizard_progress_activity_configuration_view"),

    # Error messages view
    url('errors/(?P<uploaded_file_id>\d+)/$',
        login_required(UploadedFileErrorsView.as_view()),
        name='lizard_progress_uploaded_file_error_view'),

    # Download OR DELETE an uploaded file
    url('file/(?P<measurement_id>\d+)/(?P<filename>[^/]+)$',
        views.measurement_download_or_delete,
        name='lizard_progress_filedownload'),

    # Planning page
    url('planning/$',
        login_required(views.activity.PlanningView.as_view()),
        name='lizard_progress_planningview'),
    url('planning/connect/$',
        login_required(views.activity.ConnectActivityView.as_view()),
        name='lizard_progress_connect_activity'),
    # Upload date shapefiles on the planning page
    url('planning/dates/(?P<location_type>[a-z]+)/$',
        login_required(views.activity.UploadDateShapefiles.as_view()),
        name='lizard_progress_upload_date_shapefiles'),
    # API for the tables that refresh when processing uploaded files
    url('files/$',
        login_required(views.activity.UploadedFilesView.as_view()),
        name='lizard_progress_uploaded_files_api'),
    # CSV file generation
    url('dashboardcsv/$', login_required(DashboardCsvView.as_view()),
        name='lizard_progress_dashboardcsvview'),

    # Download files
    url('^download/(?P<filetype>[^/]+)/(?P<filename>[^/]+)$',
        login_required(DownloadView.as_view()),
        name='lizard_progress_activity_downloadview'),
    # Activity dashboard
    url('$',
        views.activity.ActivityDashboard.as_view(),
        name='lizard_progress_activity_dashboard'),
]


project_urls = [
    # Kaartlagen view
    url('^map/$', login_required(InlineMapView.as_view()),
        name='lizard_progress_inlinemapview'),

    # NEW MAP
    url('^map_new/$', login_required(InlineMapViewNew.as_view()),
        name='lizard_progress_inlinemapview_new'),

    url('^map_new/.*/get_closest_to.*$', login_required(views.get_closest_to),
        name='lizard_progress_get_closest_to'),

    url('^map_new/xsecimage.*$', login_required(views.xsecimage),
        name='lizard_progress_xsecimage'),

    url('^map_new/location_code/(?P<location_code>[^/]+)/$',
        login_required(InlineMapViewNew.as_view()),
        name='lizard_progress_mapview_location_code'),
    url('^map_new/change_request/(?P<change_request>[^/]+)/$',
        login_required(InlineMapViewNew.as_view()),
        name='lizard_progress_newmap_change_request'),
    # END NEW MAP
    
    url('^mapinline/$', login_required(MapView.as_view()),
        name='lizard_progress_mapview'),
    url('^map/change_request/(?P<change_request>[^/]+)/$',
        login_required(InlineMapView.as_view()),
        name='lizard_progress_mapview_change_request'),
    # Dashboard page
    url('^dashboard/$', login_required(DashboardView.as_view()),
        name='lizard_progress_dashboardview'),
    url('^activities/$', login_required(ActivitiesView.as_view()),
        name='lizard_progress_activitiesView'),

    # Edit activities
    url('^edit_activities/$',
        login_required(views.EditActivities.as_view()),
        name='lizard_progress_edit_activities'),
    url('^delete_activity/(?P<activity_id>\d+)/$',
        login_required(views.DeleteActivity.as_view()),
        name='lizard_progress_delete_activity'),

    # Remove an uploaded file
    url('^upload/remove_uploaded_file/(?P<uploaded_file_id>\d+)/$',
        login_required(views.remove_uploaded_file_view),
        name='lizard_progress_remove_uploaded_file'),

    # Project uploads
    url('^project_file_upload/$',
        login_required(views.UploadProjectFileView.as_view()),
        name='lizard_progress_upload_projectfile'),
    url('^monstervakken_upload/$',
        login_required(views.UploadHydrovakkenView.as_view()),
        name='lizard_progress_upload_hydrovakken'),

    # Download page
    url('^download/$',
        login_required(DownloadHomeView.as_view()),
        name='lizard_progress_downloadhomeview'),
    url('^download/(?P<filetype>[^/]+)/(?P<filename>[^/]+)$',
        login_required(DownloadView.as_view()),
        name='lizard_progress_downloadview'),

    # Start an export run
    url('^export_run/(?P<export_run_id>[\d]+)/$',
        login_required(views.start_export_run_view),
        name="lizard_progress_start_export_run_view"),
    url('^export_run/(?P<export_run_id>[\d]+)/download/',
        login_required(views.download_export_run),
        name="lizard_progress_download_export_run_view"),

    # Configuration
    url('^config/$',
        login_required(views.ConfigurationView.as_view()),
        name="lizard_progress_project_configuration_view"),

    url('^email_config/$',
        login_required(views.EmailNotificationConfigurationView.as_view()),
        name="lizard_progress_project_email_config_view"),

    # Everything relating to a specific activity in this project
    url(r'^(?P<activity_id>\d+)/', include(activity_urls))
]

reviewproject_urls = [

    # Specific ReviewProject details:
    url(r'^$',
        login_required(views.ReviewProjectView.as_view()),
        name='lizard_progress_reviewproject'),

    # Upload new reviews

    # Apply filter

    # Download reviews
    url(r'^download/$',
            login_required(views.DownloadReviewProjectReviewsView.as_view()),
            name='lizard_progress_download_reviews'),
    # Download shapefile zip
    url(r'download_shapefile/$',
        login_required(views.DownloadReviewProjectShapefilesView.as_view()),
        name='lizard_progress_download_shapefiles'),
    # Finish project?

]

urlpatterns = patterns(
    '',
    # Homepage
    url('^$',
        login_required(ProjectsView.as_view()),
        name='lizard_progress_projecten'),

    # Administration pages from projectspage
    url('^newproject/$',
        login_required(views.NewProjectView.as_view()),
        name='lizard_progress_newproject'),
    url('^admin/organization/errorconfiguration/$',
        login_required(
            organization_admin.OrganizationAdminConfiguration.as_view()),
        name='lizard_progress_admin_organization_errorconfiguration'),

    # User management
    url('users/$', login_required(views.UserManagementView.as_view()),
        name="lizard_progress_user_management"),
    url('users/(?P<user_id>\d+)/$',
        login_required(views.SingleUserManagementView.as_view()),
        name="lizard_progress_single_user_management"),
    url('users/newuser/$',
        login_required(views.NewUserManagementView.as_view()),
        name="lizard_progress_new_user_management"),

    # Measurement type visibility
    url('^editvisibility/$',
        login_required(
            organization_admin.VisibleMeasurementTypes.as_view()),
        name='lizard_progress_editvisibility'),

    # Archive a project
    url('^archive/$',
        login_required(views.ArchiveProjectsOverview.as_view()),
        name='lizard_progress_archive_overview'),
    url('^archive/(?P<project_slug>[^/]+)$',
        login_required(views.ArchiveProjectsView.as_view()),
        name='lizard_progress_archive'),

    # Organization documents
    url('^download/organization/(?P<organization_id>\d+)/(?P<filename>[^/]+)',
        login_required(DownloadOrganizationDocumentView.as_view()),
        name='lizard_progress_download_organization_document'),
    url('^projects/documents/download/$',
        login_required(DownloadDocumentsView.as_view()),
        name='lizard_progress_documents_download'),

    # This is where uploads happen
    url('^upload/$',
        login_required(UploadDialogView.as_view()),
        name='lizard_progress_uploaddialogview'),

    url('^organization_file_upload/$',
        login_required(views.UploadOrganizationFileView.as_view()),
        name='lizard_progress_upload_orgfile'),

    # Graph with all cross sections of a certain location_code
    url('^crosssections/(?P<organization_id>\d+)/(?P<location_id>[^/]+)$',
        login_required(views.views.multiproject_crosssection_graph),
        name='crosssection_graph'),

    # ReviewProjects overview
    url(r'^reviews/$',
        login_required(views.ReviewProjectsOverview.as_view()),
        name='lizard_progress_reviews_overview'),

    # Create new ReviewProject
    url(r'^newreviewproject/$',
        login_required(views.NewReviewProjectView.as_view()),
        name='lizard_progress_new_reviewproject'),

    # All URLS related to some specific review project
    url(r'^reviews/(?P<review_id>[0-9]+)/', include(reviewproject_urls)),

    # All URLs related to some specific project
    url(r'^projects/(?P<project_slug>[^/]+)/', include(project_urls))

)


urlpatterns += debugmode_urlpatterns()
