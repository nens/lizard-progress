# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

""" """

# Python 3 is coming
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import logging

from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.http import Http404
from django.http import HttpResponseRedirect
from django.http import HttpResponse

from lizard_progress.views import ProjectsView
from lizard_progress import models as pmodels

from . import models
from . import forms

logger = logging.getLogger(__name__)


class ChangeRequestsPage(ProjectsView):
    template_name = 'changerequests/overview.html'
    active_menu = "requests"

    def open_requests(self):
        requests = models.Request.open_requests_for_profile(
                self.project, self.profile)

        for request in requests:
            request.view = self
        return requests

    def recently_closed_requests(self):
        if not self.user_is_uploader():
            return None

        requests = list(
            models.Request.closed_requests().filter(
                contractor=self.contractor(),
                seen=False))
        for request in requests:
            request.view = self
        return requests


class AllClosedChangeRequestsPage(ProjectsView):
    template_name = 'changerequests/closed_overview.html'
    active_menu = 'requests'

    def closed_requests(self):
        requests = models.Request.closed_requests_for_profile(
                self.project, self.profile)

        for request in requests:
            request.view = self
        return requests


class RequestDetailPage(ProjectsView):
    template_name = 'changerequests/detail.html'
    active_menu = 'requests'

    def dispatch(self, request, project_slug, request_id):
        try:
            self.changerequest = models.Request.objects.get(pk=request_id)
            self.changerequest.check_validity()
        except models.Request.DoesNotExist:
            raise Http404()

        if self.changerequest.contractor.project.slug != project_slug:
            # Trickery
            raise Http404()

        self.request = request
        self.project_slug = project_slug

        return super(RequestDetailPage, self).dispatch(
            request, project_slug=project_slug)

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
        return self.contractor() == self.changerequest.contractor


class PostRequestDetailComment(RequestDetailPage):
    def post(self, request, project_slug):
        self.comment_form = self.make_form(
            forms.RequestDetailCommentForm, self.request.POST)

        if self.comment_form.is_valid():
            self.changerequest.record_comment(
                comment=self.comment_form.cleaned_data['comment'],
                user=self.request.user)

        return HttpResponseRedirect(
            self.changerequest.detail_url())


class ChangeRequestMotivation(RequestDetailPage):
    def post(self, request, project_slug):
        self.motivation_form = self.make_form(
            forms.RequestDetailMotivationForm, self.request.POST)

        if self.motivation_form.is_valid():
            self.changerequest.motivation = (
                self.motivation_form.cleaned_data['motivation'])
            self.changerequest.save()

        return HttpResponseRedirect(
            self.changerequest.detail_url())


class AcceptOrRefuseRequest(RequestDetailPage):
    def post(self, request, project_slug):
        if 'accept' in request.POST:
            if not self.user_is_manager():
                raise PermissionDenied()
            # Do accept
            self.changerequest.accept()
        elif 'refuse' in request.POST:
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
                return self.get(request, project_slug)
        elif 'withdraw' in request.POST:
            if not self.user_is_uploader() or self.user_is_manager():
                raise PermissionDenied()
            self.changerequest.withdraw()

        return HttpResponseRedirect(
            self.changerequest.detail_url())


class NewRequestView(ProjectsView):
    template_name = "changerequests/new_request.html"
    active_menu = "requests"

    def get_form_class(self, request_type):
        if self.user_is_manager():
            # A manager has to choose which contractor this request is for
            contractors = [
                (contractor.id, unicode(contractor.organization))
                for contractor in self.project.contractor_set.select_related()]
        else:
            # Don't show field
            contractors = []

        mtypes = [
            (mtype.mtype.id, unicode(mtype.mtype))
            for mtype in self.project.measurementtype_set.all()]

        return forms.new_request_form_factory(
            self.project, request_type, mtypes, contractors)

    def chosen_contractor(self):
        """Assume form was valid, which contractor was chosen?"""
        if self.user_is_manager():
            return pmodels.Contractor.objects.get(
                pk=self.form.cleaned_data['contractor'])
        else:
            return self.contractor()

    def chosen_measurement_type(self):
        if 'mtype' in self.form.cleaned_data:
            return pmodels.AvailableMeasurementType.objecs.get(
                pk=self.form.cleaned_data['mtype'])
        else:
            # There is only one?
            return pmodels.AvailableMeasurementType.objects.filter(
                measurementtype__project=self.project).get()

    def get(self, request, project_slug):
        if not hasattr(self, 'form'):
            self.form = self.get_form_class(
                request_type=self.request_type)()

        return super(NewRequestView, self).get(request, project_slug)

    def post(self, request, project_slug):
        self.form = self.get_form_class(
            request_type=self.request_type)(request.POST)

        if self.form.is_valid():
            self.create_new_request()
            return HttpResponseRedirect(reverse(
                    'changerequests_main',
                    kwargs={'project_slug': self.project_slug}))

        return self.get(request, project_slug)

    def url(self):
        return reverse(
            self.url_name,
            kwargs={'project_slug': self.project_slug})


class NewRequestNewLocation(NewRequestView):
    request_type = models.Request.REQUEST_TYPE_NEW_LOCATION
    description = "Nieuwe of vervangende locatiecode"
    url_name = 'changerequests_newlocation'

    def create_new_request(self):
        models.Request.objects.create(
            contractor=self.chosen_contractor(),
            mtype=self.chosen_measurement_type(),
            request_type=self.request_type,
            request_status=models.Request.REQUEST_STATUS_OPEN,
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
        models.Request.objects.create(
            contractor=self.chosen_contractor(),
            mtype=self.chosen_measurement_type(),
            request_type=self.request_type,
            request_status=models.Request.REQUEST_STATUS_OPEN,
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
        models.Request.objects.create(
            contractor=self.chosen_contractor(),
            mtype=self.chosen_measurement_type(),
            request_type=self.request_type,
            request_status=models.Request.REQUEST_STATUS_OPEN,
            location_code=self.form.cleaned_data['location_code'],
            motivation=self.form.cleaned_data['motivation'])


class RequestSeen(ProjectsView):
    def post(self, request, project_slug, request_id):
        try:
            changerequest = models.Request.objects.get(pk=request_id)
        except models.Request.DoesNotExist:
            raise Http404()

        if self.contractor() == changerequest.contractor:
            changerequest.seen = True
            changerequest.save()

        return HttpResponse("OK")
