# coding=utf8
"""Forms, mainly used as steps by form wizards."""

from itertools import chain

from django import forms
from django.contrib.auth.models import User
from lizard_progress.models import (AvailableMeasurementType, Contractor,
                                    Project, Organization)
from lizard_progress.views import UploadShapefilesView
from django.utils.html import conditional_escape
from django.utils.encoding import force_unicode
from django.utils.safestring import mark_safe

import os

import logging

logger = logging.getLogger(__name__)


class ProjectForm(forms.ModelForm):
    name = forms.CharField(max_length=50)

    def __init__(self, *args, **kwargs):
        self.user = kwargs.get('initial').pop('superuser')
        super(ProjectForm, self).__init__(*args, **kwargs)

        usernames = [u.username for u in
                     Organization.users_in_same_organization(self.user)]
        self.fields['superuser'].queryset = \
            User.objects.filter(username__in=usernames)

    def clean_name(self):
        """Validates and returns the name of a new project."""
        # Since the `slug` field is excluded, it will not
        # be checked automatically for uniqueness.
        name = self.cleaned_data['name']
        usernames = list(
            Organization.users_in_same_organization(self.user))
        if Project.objects.filter(
            name=name, superuser__in=usernames).exists():
            msg = "Kies a.u.b. een andere Projectnaam."
            raise forms.ValidationError(msg)
        return name

    class Meta:
        model = Project
        exclude = ('slug',)


USER_CHOICES = (
    ('1', 'Een bestaand account hergebruiken'),
    ('2', 'Een nieuw account aanmaken'),
)


class ContractorForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(ContractorForm, self).__init__(*args, **kwargs)
        self.fields['project'].queryset = (
            Project.objects.filter(superuser=user))

    class Meta:
        model = Contractor
        exclude = ('slug', 'name',)


class ProjectChoiceForm(forms.Form):
    """Form that allows the selection of a single `Project`.

    The currently logged-in user can only choose from
    projects he owns (i.e. is superuser of).
    """

    project = forms.ModelChoiceField(queryset=None)

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(ProjectChoiceForm, self).__init__(*args, **kwargs)
        self.fields['project'].queryset = \
            Project.objects.filter(superuser=user)


class ContractorChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, contractor):
        return contractor.organization.name


class ContractorChoiceForm(forms.Form):
    """Form that allows the selection of a single `Contractor`.

    The currently logged-in user can only choose from
    contractors associated with the `Project` that
    was selected in a previous step.
    """

    contractor = ContractorChoiceField(queryset=None, label='Opdrachtnemer')

    def __init__(self, *args, **kwargs):
        project = kwargs.pop('project', None)
        super(ContractorChoiceForm, self).__init__(*args, **kwargs)
        self.fields['contractor'].queryset = \
            Contractor.objects.filter(project=project)


class MtypeCheckboxSelectMultiple(forms.CheckboxSelectMultiple):
    def render(self, name, value, attrs=None, choices=()):
        if value is None:
            value = []
        has_id = attrs and 'id' in attrs
        final_attrs = self.build_attrs(attrs, name=name)
        output = [u'<ul>']

        # Normalize to strings
        str_values = set([force_unicode(v) for v in value])
        for i, (option_value, option_label) in enumerate(
            chain(self.choices, choices)):
            # If an ID attribute was given, add a numeric index as a suffix,
            # so that the checkboxes don't all have the same ID attribute.
            if has_id:
                final_attrs = dict(final_attrs, id='%s_%s' % (attrs['id'], i))
                label_for = u' for="%s"' % final_attrs['id']
            else:
                label_for = ''

            # Hack
            from lizard_progress.models import AvailableMeasurementType
            mtype = AvailableMeasurementType.objects.get(pk=option_value)

            cb = forms.CheckboxInput(
                final_attrs, check_test=lambda value: value in str_values)
            option_value = force_unicode(option_value)
            rendered_cb = cb.render(name, option_value)
            option_label = conditional_escape(force_unicode(option_label))
            output.append(
                u'''<li><label%s>%s %s</label><br>
                       <span><i>%s</i></span>
                    </li>''' %
                (label_for, rendered_cb, option_label, mtype.description))
        output.append(u'</ul>')
        return mark_safe(u'\n'.join(output))

    def id_for_label(self, id_):
        # See the comment for RadioSelect.id_for_label()
        if id_:
            id_ += '_0'
        return id_


class MeasurementTypeForm(forms.Form):
    """Displays `AvailableMeasurementTypes` to choose from."""

    measurement_types = forms.ModelMultipleChoiceField(
        widget=MtypeCheckboxSelectMultiple,
        queryset=AvailableMeasurementType.objects.all().order_by('name'),
        label="Uit te voeren werkzaamheden"
    )


def needs_shapefile_condition(wizard):
    """Returns False if the ShapeFileForm step should be skipped."""
    cleaned_data = wizard.get_cleaned_data_for_step('2') or {}
    project = (wizard.get_cleaned_data_for_step('0') or {}).get('project')
    if not project:
        return True

    return any(project.needs_predefined_locations(measurement_type)
               for measurement_type in
               cleaned_data.get('measurement_types', ()))


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


class ShapefileForm(forms.Form):
    """Form for uploading a shapefile."""

    dbf = ExtFileField(exts=[".dbf"])
    prj = ExtFileField(exts=[".prj"], required=False, help_text="(Optioneel)")
    shp = ExtFileField(exts=[".shp"])
    shx = ExtFileField(exts=[".shx"])

    def clean(self):
        cleaned_data = super(ShapefileForm, self).clean()

        if self.errors:
            return cleaned_data

        # Since there are no errors, `cleaned_data` has all required fields.

        dbf = os.path.splitext(cleaned_data.get("dbf").name)[0]
        shp = os.path.splitext(cleaned_data.get("shp").name)[0]
        shx = os.path.splitext(cleaned_data.get("shx").name)[0]

        # According to http://en.wikipedia.org/wiki/Shapefile,
        # a `.prj` file is not mandatory, but if it is not
        # absent, it has to have the same filename.

        prj = cleaned_data.get("prj", None)
        if prj:
            prj = os.path.splitext(prj.name)[0]
        else:
            prj = dbf

        if dbf == prj == shp == shx:
            pass
        else:
            msg = ("De geselecteerde bestanden horen "
                   + "niet tot dezelfde shapefile.")
            raise forms.ValidationError(msg)

        return cleaned_data


class CalculateForm(forms.Form):
    """cccc"""
    error_messages = {
        'no_mothershape': (u'De opdrachtnemer heeft nog ' +
                           u'geen (moeder)shapefile geüpload.'),
    }

    def __init__(self, *args, **kwargs):
        self.contractor = kwargs.pop('contractor', None)
        super(CalculateForm, self).__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super(CalculateForm, self).clean()
        if not self.has_mothershape:
            raise forms.ValidationError(
                CalculateForm.error_messages['no_mothershape'])
        return cleaned_data

    @property
    def has_mothershape(self):
        """Returns `True` if an uploaded shapefile is present."""
        directory = UploadShapefilesView.get_directory(self.contractor)
        return bool(
            [fn for fn in os.listdir(directory) if fn.endswith('.shp')])
