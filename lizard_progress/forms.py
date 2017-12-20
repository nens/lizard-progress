# coding=UTF-8
"""Forms, mainly used as steps by form wizards."""

from tls import request  # ! So that form validation can know about
                         # the current user

from django import forms
from django.contrib.auth import models as authmodels
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from jsonfield.fields import JSONFormField
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
                msg = _("Incorrect file format.")
                raise forms.ValidationError(msg)


def project_name_validator(name):
    organization = models.Organization.get_by_user(request.user)
    if not organization:
        raise ValidationError(_("No organization found!"))

    if models.Project.objects.filter(
            organization=organization, name=name).exists():
        raise ValidationError(_("This project name already exists."))


class NewProjectForm(forms.Form):
    NUM_ACTIVITIES = 5

    def __init__(self, *args, **kwargs):
        if 'organization' in kwargs:
            self.organization = kwargs['organization']
            del kwargs['organization']
        else:
            self.organization = None

        super(NewProjectForm, self).__init__(*args, **kwargs)

        self.fields['ptype'] = forms.ModelChoiceField(
            widget=forms.Select(attrs={'class' : 'form-control'}),
            label=_("Project type (optional)"),
            queryset=models.ProjectType.objects.filter(
                organization=self.organization),
            required=False)

        for i in range(1, 1 + self.NUM_ACTIVITIES):
            self.fields['contractor' + str(i)] = forms.ModelChoiceField(
                widget=forms.Select(
                    attrs={
                        'class' : 'form-control selectpicker',
                        'data-live-search': 'true'
                    }
                ),
                label=_("Contractor/viewer") + " " + str(i),
                queryset=models.Organization.objects.all(),
                required=False
            )

            self.fields['measurementtype' + str(i)] = forms.ModelChoiceField(
                widget=forms.Select(attrs={'class' : 'form-control'}),
                label=_("Measurement type") + " " + str(i),
                queryset=self.organization.
                visible_available_measurement_types(),
                required=False
            )

            self.fields['activity{}'.format(i)] = forms.CharField(
                widget=forms.TextInput(attrs={'class' : 'form-control'}),
                label=_('Activity (name, optional)') + " " + str(i),
                max_length=100, required=False)

    def clean(self):
        cleaned_data = super(NewProjectForm, self).clean()

        if self.errors:
            return cleaned_data

        for i in range(1, 1 + self.NUM_ACTIVITIES):
            data = [cleaned_data.get(field + str(i))
                    for field in ('activity', 'contractor', 'measurementtype')]
            if any(data[1:]) and not all(data[1:]):
                self._errors['contractor' + str(i)] = self.error_class([
                    _("Not all activity fields filled in.")])

        return cleaned_data

    name = forms.CharField(
        widget=forms.TextInput(attrs={'class' : 'form-control'}),
        label=_("Project name"),
        max_length=50,
        validators=[project_name_validator])


class SingleUserForm(forms.Form):
    username = forms.RegexField(
        widget=forms.TextInput(attrs={'class' : 'form-control'}),
        label="Gebruikersnaam", max_length=30, regex=r"^[\w.@+-]+$",
        help_text=_(
            "Required. 30 characters or fewer. Letters, digits and "
            "@/./+/-/_ only."),
        error_messages={
            'invalid': _("This value may contain only letters, numbers and "
                         "@/./+/-/_ characters.")})

    first_name = forms.CharField(
        widget=forms.TextInput(attrs={'class' : 'form-control'}),
        label="Voornaam", max_length=30, required=False)
    last_name = forms.CharField(
        widget=forms.TextInput(attrs={'class' : 'form-control'}),
        label="Achternaam", max_length=30, required=False)

    email = forms.EmailField(
        widget=forms.TextInput(attrs={'class' : 'form-control'}),
        label="Email adres",
        required=False)

    new_password1 = forms.CharField(
        label=_("New password"), required=False,
        widget=forms.PasswordInput(attrs={'class' : 'form-control'}))
    new_password2 = forms.CharField(
        label=_("New password confirmation"), required=False,
        widget=forms.PasswordInput(attrs={'class' : 'form-control'}))

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
            widget=forms.CheckboxInput(attrs={'class': 'form-control'}),
            label="Mag uploaden", initial=initial_uploader, required=False)

        # This field is only allowed in organizations that have projects
        if ((self.edited_user and profile.organization.is_project_owner) or
                show_admin_role):
            self.fields['is_manager'] = forms.BooleanField(
                widget=forms.CheckboxInput(attrs={'class': 'form-control'}),
                label="Mag projecten beheren", initial=initial_manager,
                required=False)

        # Admins (user managers) can't set their own admin status, for
        # safety
        if not editing_self:
            self.fields['is_admin'] = forms.BooleanField(
                widget=forms.CheckboxInput(attrs={'class': 'form-control'}),
                label="Mag gebruikers beheren", initial=initial_admin,
                required=False)


class AddActivityForm(forms.Form):
    def __init__(self, args, project):
        super(AddActivityForm, self).__init__(args)

        self.fields['measurementtype'] = forms.ModelChoiceField(
            widget=forms.Select(attrs={'class' : 'form-control'}),
            label=_("Measurement type"),
            queryset=project.organization
            .visible_available_measurement_types(),
            required=True)

    contractor = forms.ModelChoiceField(
        widget=forms.Select(attrs={'class' : 'form-control'}),
        label=_("Contractor/viewer"),
        queryset=models.Organization.objects.all(),
        required=True)

    description = forms.CharField(
        widget=forms.TextInput(attrs={'class' : 'form-control'}),
        label=_('Description (optional)'), required=False, max_length=100)


class ShapefileForm(forms.Form):
    """Form for uploading a shapefile."""
    dbf = ExtFileField(exts=[".dbf"], label=".dbf bestand")
    shp = ExtFileField(exts=[".shp"], label=".shp bestand")
    shx = ExtFileField(exts=[".shx"], label=".shx bestand")

    def clean(self):
        cleaned_data = super(ShapefileForm, self).clean()
        if self.errors:
            return cleaned_data
        # Since there are no errors, `cleaned_data` has all required fields.
        dbf = os.path.splitext(cleaned_data.get("dbf").name)[0]
        shp = os.path.splitext(cleaned_data.get("shp").name)[0]
        shx = os.path.splitext(cleaned_data.get("shx").name)[0]
        if dbf == shp == shx:
            pass
        else:
            msg = ("De geselecteerde bestanden horen "
                   + "niet tot dezelfde shapefile.")
            raise forms.ValidationError(msg)
        return cleaned_data


class RibxForm(forms.Form):
    """Form for uploading a RIBX(A) file."""
    ribx = ExtFileField(
        exts=[".ribx", ".ribxa", ".xml"], label="RIBX(A) bestand")


class ConnectActivityForm(forms.Form):
    def __init__(self, activity, *args, **kwargs):
        super(ConnectActivityForm, self).__init__(*args, **kwargs)
        self.fields['activity'] = forms.ModelChoiceField(
            label=_('Activity'), queryset=models.Activity.objects.filter(
                project=activity.project).exclude(
                pk=activity.id))


class NewReviewProjectForm(forms.Form):

    name = forms.CharField(label='name', max_length=50)
    # (inspection)Project
    ribx = ExtFileField(
        exts=[".ribx", ".ribxa", ".xml"],
        label="ribx")

    def __init__(self, *args, **kwargs):
        if 'organization' in kwargs:
            self.organization = kwargs['organization']
            del kwargs['organization']
        else:
            self.organization = None

        super(NewReviewProjectForm, self).__init__(*args, **kwargs)


class UploadReviews(forms.Form):

    reviews = JSONFormField(label='reviews')

