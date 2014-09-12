# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

""" """

# Python 3 is coming
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext as _

from . import models
from lizard_progress import models as pmodels


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


def _open_request_exists(project, mtype_id, **kwargs):
    # Query to see if the request already exists
    existing_request_queryset = models.Request.objects.filter(
        contractor__project=project,
        request_status=models.Request.REQUEST_STATUS_OPEN,
        **kwargs)

    # If there is more than one mtype (and the user was asked for that
    # too), then check if the existing request is of the same mtype
    if mtype_id is not None:
        existing_request_queryset = existing_request_queryset.filter(
            mtype__id=mtype_id)

    return existing_request_queryset.exists()


def new_request_form_factory(
    project, request_type, mtypes=(), contractors=()):
    """Create a class that represents the exact form we currently
    need; forms are slightly different based on who is filling one in
    (project owner or contractor) and on the type of request.

    This Form class is created dynamically, to fit for each request
    type.  The types have fields and checks in common, but there are
    differences too. Both fields and methods are optionally defined.
    Note that the variables 'project', 'request_type' and so on, which
    are used in if statements and clean_ methods, are defined in this
    function, not in the class."""

    class NewRequestForm(forms.Form):
        if contractors:
            contractor = forms.ChoiceField(
                label="Opdrachtnemer", choices=contractors, required=True)

        if len(mtypes) > 1:
            mtype = forms.ChoiceField(
                label="Soort werkzaamheid", choices=mtypes, required=True)

        location_code = forms.CharField(
            label="Locatiecode", required=True)

        def clean_location_code(self):
            location_code = self.data['location_code']
            try:
                location = pmodels.Location.objects.get(
                    project=project, location_code=location_code)
            except pmodels.Location.DoesNotExist:
                location = None

            if request_type == models.Request.REQUEST_TYPE_NEW_LOCATION:
                if location:
                    raise ValidationError(
                        _('Location already exists.'))
            else:
                if not location:
                    raise ValidationError(
                        _('Location does not exist.'))

            mtype = self.data.get('mtype')
            if (_open_request_exists(
                    project, mtype, location_code=location_code) or
                _open_request_exists(
                    project, mtype, old_location_code=location_code)):
                raise ValidationError(
                    _("There is already an open request for this location."))

            return location_code

        if request_type == models.Request.REQUEST_TYPE_NEW_LOCATION:
            old_location_code = forms.CharField(
                label="Oude locatiecode",
                help_text="Alleen nodig als de nieuwe code deze vervangt",
                required=False)

            def clean_old_location_code(self):
                """If given, the old location must exist and there
                cannot be an existing request using this location
                yet."""
                old_location_code = self.data.get('old_location_code')
                if not old_location_code:
                    return None  # It's optional

                try:
                    pmodels.Location.objects.get(
                        project=project,
                        location_code=old_location_code)
                except pmodels.Location.DoesNotExist:
                    raise ValidationError(_(
                            "Old location doesn't exist."))

                mtype = self.data.get('mtype')
                if (_open_request_exists(
                        project, mtype, location_code=old_location_code) or
                    _open_request_exists(
                        project, mtype, old_location_code=old_location_code)):
                    raise ValidationError(
                        _("There is already an open request "
                          "for this location."))

                return old_location_code

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


class RefusalForm(forms.Form):
    reason = forms.CharField(label="Reden", required=True)
    old_location_code = forms.CharField(
        label="Oude locatiecode", required=False)


class PossibleRequestForm(forms.Form):
    motivation = forms.CharField(label="Reden", required=True)
