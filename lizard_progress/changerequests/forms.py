# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

""" """

# Python 3 is coming
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from django import forms

from . import models


class ChangeRequestsForm(forms.Form):
    """Subclass of Form that always receives a request, a project slug
    and optionally a changerequest, along with its other arguments,
    and sets them as attributes."""

    def __init__(self, *args, **kwargs):
        """Request, project_slug and request_id must be passed as kwargs."""

        self.request = kwargs.pop('request')
        self.project_slug = kwargs.pop('project_slug')
        self.changerequest = kwargs.pop('changerequest', None)

        return super(ChangeRequestsForm, self).__init__(*args, **kwargs)


class RequestDetailCommentForm(ChangeRequestsForm):
    comment = forms.CharField(min_length=1)


class RequestDetailMotivationForm(ChangeRequestsForm):
    motivation = forms.CharField(min_length=1)


def new_request_form_factory(request_type, mtypes=(), contractors=()):
    """Create a class that represents the exact form we currently
    need; forms are slightly different based on who is filling one in
    (project owner or contractor) and on the type of request."""

    class NewRequestForm(forms.Form):
        if contractors:
            contractor = forms.ChoiceField(
                label="Opdrachtnemer", choices=contractors, required=True)

        if len(mtypes) > 1:
            mtype = forms.ChoiceField(
                label="Soort werkzaamheid", choices=mtypes, required=True)

        location_code = forms.CharField(
            label="Locatiecode", required=True)

        if request_type == models.Request.REQUEST_TYPE_NEW_LOCATION:
            old_location_code = forms.CharField(
                label="Oude locatiecode",
                help_text="Alleen nodig als de nieuwe code deze vervangt",
                required=False)

        if request_type in (
            models.Request.REQUEST_TYPE_NEW_LOCATION,
            models.Request.REQUEST_TYPE_MOVE_LOCATION):
            rd_x = forms.FloatField(
                label="X-coordinaat",
                help_text="In Rijksdriehoekprojectie",
                required=True)
            rd_y = forms.FloatField(
                label="Y-coordinaat",
                help_text="In Rijksdriehoekprojectie",
                required=True)

        motivation = forms.CharField(
            label="Motivatie", required=True,
            widget=forms.Textarea)

    return NewRequestForm
