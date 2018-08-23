# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

""" """

# Python 3 is coming
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import json
import logging

from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.http import Http404
from django.http import HttpResponseRedirect
from django.http import HttpResponse

from lizard_progress.views.activity import ActivityView
from lizard_progress import models as pmodels

from . import models
from . import forms

logger = logging.getLogger(__name__)


def JSONResponse(ob):
    return HttpResponse(
        json.dumps(ob), mimetype="application/json")


class ChangeRequestsPage(ActivityView):
    template_name = 'changerequests/overview.html'
    active_menu = "requests"

    def open_requests(self):
        requests = models.Request.open_requests_for_profile(
            self.activity, self.profile)

        for request in requests:
            # This is a hack that ensures that request.did_last_action can
            # access some of the view's information. Dirty.
            request.view = self
        return requests

    def recently_closed_requests(self):
        if not self.user_is_activity_uploader():
            return None

        requests = list(
            models.Request.closed_requests().filter(
                activity=self.activity,
                seen=False))
        for request in requests:
            request.view = self
        return requests


class AllClosedChangeRequestsPage(ActivityView):
    template_name = 'changerequests/closed_overview.html'
    active_menu = 'requests'

    def closed_requests(self):
        requests = models.Request.closed_requests_for_profile(
            self.activity, self.profile)

        for request in requests:
            request.view = self
        return requests


class RequestDetailPage(ActivityView):
    template_name = 'changerequests/detail.html'
    active_menu = 'requests'

    def dispatch(self, request, project_slug, activity_id, request_id):
        try:
            self.changerequest = models.Request.objects.get(pk=request_id)
            self.changerequest.check_validity()
        except models.Request.DoesNotExist:
            raise Http404()

        if self.changerequest.activity.project.slug != project_slug:
            # Trickery
            raise Http404()

        self.request = request
        self.project_slug = project_slug

        return super(RequestDetailPage, self).dispatch(
            request, project_slug=project_slug, activity_id=activity_id)

    def make_form(self, formclass, *args, **kwargs):
        """Helper to create forms, because we always pass request,
        project slug and changerequest as helper kwargs."""

        kwargs.update({
            'request': self.request,
            'project_slug': self.project_slug,
            'changerequest': self.changerequest
        })

        return formclass(*args, **kwargs)

    def user_is_contractor(self):
        """User is with the organization that is contractor for this
        activity."""
        return self.activity.contractor.contains_user(self.request.user)


class PostRequestDetailComment(RequestDetailPage):
    def post(self, request, project_slug):
        self.comment_form = self.make_form(
            forms.RequestDetailCommentForm, self.request.POST)

        if self.comment_form.is_valid():
            self.changerequest.record_comment(
                comment=self.comment_form.cleaned_data['comment'],
                user=self.request.user)

        return HttpResponseRedirect(
            self.changerequest.get_absolute_url())


class ChangeRequestMotivation(RequestDetailPage):
    def post(self, request, project_slug):
        self.motivation_form = self.make_form(
            forms.RequestDetailMotivationForm, self.request.POST)

        if self.motivation_form.is_valid():
            self.changerequest.motivation = (
                self.motivation_form.cleaned_data['motivation'])
            self.changerequest.save()

        return HttpResponseRedirect(
            self.changerequest.get_absolute_url())


class AcceptOrRefuseRequest(RequestDetailPage):
    def post(self, request, project_slug):
        wantsjson = request.POST.get('wantoutputas') == 'json'
        redir = request.POST.get('redirecturl', '')

        if request.POST.get('accept'):
            if not self.user_is_manager():
                raise PermissionDenied()
            # Do accept
            self.changerequest.accept()
        elif request.POST.get('refuse'):
            if not self.user_is_manager():
                raise PermissionDenied()
            # Refusal needs a reason
            self.refusal_form = forms.RefusalForm(request.POST)
            if self.refusal_form.is_valid():
                # Do refuse
                self.changerequest.refuse(
                    self.refusal_form.cleaned_data['reason'])
            else:
                # Set error and render get
                self.acceptance_error = "Afwijzing kan alleen met reden."
                if wantsjson:
                    return JSONResponse({
                        'success': False, 'error': self.acceptance_error})
                else:
                    return self.get(request, project_slug)
        elif request.POST.get('withdraw'):
            if not self.user_is_activity_uploader() or self.user_is_manager():
                raise PermissionDenied()
            self.changerequest.withdraw()

        if wantsjson:
            res = {'success': True,
                   'id': self.changerequest.id}
            if redir:
                res['redirurl'] = redir

            return JSONResponse(res)
        else:
            return HttpResponseRedirect(
                self.changerequest.get_absolute_url())


class NewRequestView(ActivityView):
    template_name = "changerequests/new_request.html"
    active_menu = "requests"

    def get_form_class(self, request_type):
        return forms.new_request_form_factory(self.activity, request_type)

    def get(self, request, project_slug):
        if not hasattr(self, 'form'):
            self.form = self.get_form_class(
                request_type=self.request_type)()

        return super(NewRequestView, self).get(request, project_slug)

    def post(self, request, project_slug):
        self.form = self.get_form_class(
            request_type=self.request_type)(request.POST)

        if self.form.is_valid():
            request = self.create_new_request()

            if request.created_by_manager:
                # Auto accept
                request.accept()

            return HttpResponseRedirect(reverse(
                'changerequests_main',
                kwargs={'project_slug': self.project_slug,
                        'activity_id': self.activity_id}))

        return self.get(request, project_slug)

    def url(self):
        return reverse(
            self.url_name,
            kwargs={'project_slug': self.project_slug,
                    'activity_id': self.activity_id})


class NewRequestNewLocation(NewRequestView):
    request_type = models.Request.REQUEST_TYPE_NEW_LOCATION
    description = "Nieuwe of vervangende locatiecode"
    url_name = 'changerequests_newlocation'

    def create_new_request(self):
        return models.Request.objects.create(
            activity=self.activity,
            request_type=self.request_type,
            request_status=models.Request.REQUEST_STATUS_OPEN,
            created_by_manager=self.user_is_manager(),
            location_code=self.form.cleaned_data['location_code'],
            old_location_code=(
                self.form.cleaned_data['old_location_code'] or None),
            motivation=self.form.cleaned_data['motivation'],
            the_geom='POINT({x} {y})'.format(
                x=self.form.cleaned_data['rd_x'],
                y=self.form.cleaned_data['rd_y']))


class NewRequestMoveLocation(NewRequestView):
    request_type = models.Request.REQUEST_TYPE_MOVE_LOCATION
    description = "Locatiecode verplaatsen"
    url_name = 'changerequests_movelocation'

    def create_new_request(self):
        return models.Request.objects.create(
            activity=self.activity,
            request_type=self.request_type,
            request_status=models.Request.REQUEST_STATUS_OPEN,
            created_by_manager=self.user_is_manager(),
            location_code=self.form.cleaned_data['location_code'],
            motivation=self.form.cleaned_data['motivation'],
            the_geom='POINT({x} {y})'.format(
                x=self.form.cleaned_data['rd_x'],
                y=self.form.cleaned_data['rd_y']))


class NewRequestRemoveCode(NewRequestView):
    request_type = models.Request.REQUEST_TYPE_REMOVE_CODE
    description = "Locatiecode laten vervallen"
    url_name = 'changerequests_removecode'

    def create_new_request(self):
        location = pmodels.Location.objects.get(
            location_code=self.form.cleaned_data['location_code'],
            activity=self.activity)

        return models.Request.create_deletion_request(
            location, self.form.cleaned_data['motivation'],
            self.user_is_manager())


class RequestSeen(ActivityView):
    def post(self, request, project_slug, request_id):
        try:
            changerequest = models.Request.objects.get(pk=request_id)
        except models.Request.DoesNotExist:
            raise Http404()

        if self.contractor() == changerequest.contractor:
            changerequest.seen = True
            changerequest.save()

        return HttpResponse("OK")


class PossibleRequestsView(ActivityView):
    template_name = "changerequests/possible_requests.html"

    def dispatch(self, request, uploaded_file_id, *args, **kwargs):
        self.uploaded_file_id = uploaded_file_id
        return super(PossibleRequestsView, self).dispatch(
            request, *args, **kwargs)

    def uploaded_file(self):
        try:
            return pmodels.UploadedFile.objects.get(
                pk=self.uploaded_file_id)
        except pmodels.UploadedFile.DoesNotExist:
            raise Http404()


class ActivatePossibleRequest(ActivityView):
    """Called from Ajax, answers in JSON."""

    def post(
            self, request, project_slug, uploaded_file_id,
            possible_request_id):
        try:
            possible_request = models.PossibleRequest.objects.get(
                uploaded_file_id=uploaded_file_id,
                pk=possible_request_id)
        except models.PossibleRequest.DoesNotExist:
            raise Http404()

        form = forms.PossibleRequestForm(request.POST)

        if not form.is_valid():
            return JSONResponse({
                'success': False,
                'error': "Motivatie is verplicht.",
                "error_span_id": (
                    "#submit-errors-{}".format(possible_request_id))
            })

        # Actually make request
        error = possible_request.activate(
            motivation=form.cleaned_data['motivation'],
            old_location_code=form.cleaned_data.get('old_location_code', None))

        if error is None:
            return JSONResponse({'success': True})
        else:
            return JSONResponse({
                'success': False,
                'error': error,
                "error_span_id": (
                    "#submit-errors-{}".format(possible_request_id))
            })
