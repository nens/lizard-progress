# coding=UTF-8
"""Forms, mainly used as steps by form wizards."""

from itertools import chain

from tls import request  # ! So that form validation can know about
                         # the current user

from django import forms
from django.contrib.auth import models as authmodels
from django.core.exceptions import ValidationError
from django.utils.encoding import force_unicode
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from lizard_progress import models

import os

import logging

logger = logging.getLogger(__name__)


USER_CHOICES = (
    ('1', 'Een bestaand account hergebruiken'),
    ('2', 'Een nieuw account aanmaken'),
)


class ExtFileField(forms.FileField):
    """A `FileField` that validates the filename extension.

    The extensions allowed are passed as a list to the
    constructor, e.g.: ExtFileField(exts=[".dbf"])
    """

    def __init__(self, *args, **kwargs):
        self.exts = [ext.lower() for ext in kwargs.pop("exts")]
        super(ExtFileField, self).__init__(*args, **kwargs)

    def validate(self, value):
        super(ExtFileField, self).validate(value)
        if value:
            ext = os.path.splitext(value.name)[1]
            if ext.lower() not in self.exts:
                msg = "Verkeerd bestandsformaat."
                raise forms.ValidationError(msg)


def project_name_validator(name):
    organization = models.Organization.get_by_user(request.user)
    if not organization:
        raise ValidationError(_("No organization found!"))

    if models.Project.objects.filter(
            organization=organization, name=name).exists():
        raise ValidationError(_("This project name already exists."))


class NewProjectForm(forms.Form):
    def __init__(self, *args, **kwargs):
        if 'organization' in kwargs:
            self.organization = kwargs['organization']
            del kwargs['organization']
        else:
            self.organization = None

        super(NewProjectForm, self).__init__(*args, **kwargs)
        self.fields['ptype'] = forms.ModelChoiceField(
            label=_("Project type (optional)."),
            queryset=models.ProjectType.objects.filter(
                organization=self.organization),
            required=False)

        self.fields['mtypes'] = forms.ModelMultipleChoiceField(
            label=_("Choose one or more measurement types"),
            queryset=self.organization.visible_available_measurement_types())

    name = forms.CharField(
        label=_("Project name"),
        max_length=50,
        validators=[project_name_validator])
    contractors = forms.ModelMultipleChoiceField(
        label=_("Choose one or more contractors"),
        queryset=models.Organization.objects.all())


class SingleUserForm(forms.Form):
    username = forms.RegexField(
        label="Gebruikersnaam", max_length=30, regex=r"^[\w.@+-]+$",
        help_text=_(
            "Required. 30 characters or fewer. Letters, digits and "
            "@/./+/-/_ only."),
        error_messages={
            'invalid': _("This value may contain only letters, numbers and "
                         "@/./+/-/_ characters.")})

    first_name = forms.CharField(
        label="Voornaam", max_length=30, required=False)
    last_name = forms.CharField(
        label="Achternaam", max_length=30, required=False)

    email = forms.EmailField(label="Email adres", required=False)

    new_password1 = forms.CharField(
        label=_("New password"), required=False,
        widget=forms.PasswordInput)
    new_password2 = forms.CharField(
        label=_("New password confirmation"), required=False,
        widget=forms.PasswordInput)

    def __init__(self, user, *args, **kwargs):
        """Store which user we are editing."""
        self.edited_user = user
        return super(SingleUserForm, self).__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super(SingleUserForm, self).clean()

        if self.errors:
            return cleaned_data

        username = cleaned_data['username']
        new_password1 = cleaned_data['new_password1']
        new_password2 = cleaned_data['new_password2']

        # Does the username exist?
        try:
            user = authmodels.User.objects.get(username=username)
            if user != self.edited_user:
                raise ValidationError("Deze gebruikersnaam bestaat al.")
        except authmodels.User.DoesNotExist:
            # Geen probleem
            pass

        if new_password1 != new_password2:
            raise ValidationError("De wachtwoorden zijn niet gelijk.")

        return cleaned_data

    def update_user(self, organization=None):
        if not self.edited_user:
            self.edited_user = authmodels.User.objects.create(
                username=self.cleaned_data['username'])
            profile = models.UserProfile.objects.create(
                user=self.edited_user,
                organization=organization)
        else:
            profile = models.UserProfile.get_by_user(self.edited_user)

        for attr in ['username', 'first_name', 'last_name', 'email']:
            data = self.cleaned_data[attr]
            setattr(self.edited_user, attr, data)

        if self.cleaned_data['new_password1']:
            self.edited_user.set_password(self.cleaned_data['new_password1'])

        for (field, role) in (
                ('is_uploader', models.UserRole.ROLE_UPLOADER),
                ('is_manager', models.UserRole.ROLE_MANAGER),
                ('is_admin', models.UserRole.ROLE_ADMIN)):
            if field in self.fields:
                if self.cleaned_data[field] and not profile.has_role(role):
                    # Add role
                    profile.roles.add(models.UserRole.objects.get(code=role))
                elif not self.cleaned_data[field] and profile.has_role(role):
                    # Remove remove
                    profile.roles.remove(
                        models.UserRole.objects.get(code=role))

        self.edited_user.save()
        return self.edited_user

    def add_role_fields(self, editing_self, show_admin_role=False):
        # Initial values
        if self.edited_user:
            profile = models.UserProfile.get_by_user(self.edited_user)
            initial_uploader = profile.has_role(models.UserRole.ROLE_UPLOADER)
            initial_manager = profile.has_role(models.UserRole.ROLE_MANAGER)
            initial_admin = profile.has_role(models.UserRole.ROLE_ADMIN)
        else:
            initial_manager = initial_admin = False
            # For organizations that can only upload, everyone is uploader
            # by default, because there's nothing else to do for them
            initial_uploader = not show_admin_role

        self.fields['is_uploader'] = forms.BooleanField(
            label="Mag uploaden", initial=initial_uploader, required=False)

        # This field is only allowed in organizations that have projects
        if ((self.edited_user and profile.organization.is_project_owner) or
                show_admin_role):
            self.fields['is_manager'] = forms.BooleanField(
                label="Mag projecten beheren", initial=initial_manager,
                required=False)

        # Admins (user managers) can't set their own admin status, for
        # safety
        if not editing_self:
            self.fields['is_admin'] = forms.BooleanField(
                label="Mag gebruikers beheren", initial=initial_admin,
                required=False)


class AddContractorMeasurementTypeForm(forms.Form):
    # We use a single form with no required fields for four different
    # submits...
    contractor = forms.IntegerField(required=False)
    measurementtype = forms.IntegerField(required=False)
    remove_contractor = forms.IntegerField(required=False)
    remove_mtype = forms.IntegerField(required=False)
