# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

""" """

# Python 3 is coming
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from django.conf.urls.defaults import patterns, url
from django.contrib.auth.decorators import login_required

from . import views

urlpatterns = patterns(
    '',
    # Overview pages
    url('^$', login_required(views.ChangeRequestsPage.as_view()),
        name='changerequests_main'),
    url('^closed/$',
        login_required(views.AllClosedChangeRequestsPage.as_view()),
        name='changerequests_closed'),

    # Note that a closed request is seen
    url(r'^detail/(?P<request_id>\d+)/set_seen/$',
        login_required(views.RequestSeen.as_view()),
        name='changerequests_set_seen'),

    # Detail page and POST functionality from here
    url(r'^detail/(?P<request_id>\d+)/$',
        login_required(views.RequestDetailPage.as_view()),
        name='changerequests_detail'),
    url(r'^detail/(?P<request_id>\d+)/add_comment/$',
        login_required(views.PostRequestDetailComment.as_view()),
        name='changerequests_detail_addcomment'),
    url(r'^detail/(?P<request_id>\d+)/change_motivation/$',
        login_required(views.ChangeRequestMotivation.as_view()),
        name='changerequests_detail_changemotivation'),
    url(r'^detail/(?P<request_id>\d+)/acceptance/$',
        login_required(views.AcceptOrRefuseRequest.as_view()),
        name='changerequests_detail_acceptorrefuse'),

    # New change request forms
    url(r'^new/new_location/$',
        login_required(views.NewRequestNewLocation.as_view()),
        name='changerequests_newlocation'),
    url(r'^new/move_location/$',
        login_required(views.NewRequestMoveLocation.as_view()),
        name='changerequests_movelocation'),
    url(r'^new/remove_code/$',
        login_required(views.NewRequestRemoveCode.as_view()),
        name='changerequests_removecode'),
)
