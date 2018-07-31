# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

"""Organizations can configure some options about checks. When they
create a new project, their default values are copied to the project,
so that they can be configured further in the project."""

# Python 3 is coming
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from collections import namedtuple

from lizard_progress import errors
from lizard_progress import models

import logging

logger = logging.getLogger(__name__)


class Option(namedtuple(
        'Option',
        'option, short_description, long_description,'
        ' type, default, only_for_error, for_project,'
        ' applies_to_measurement_types,')):

    def __init__(self, *args, **kwargs):
        super(Option, self).__init__(*args, **kwargs)

        # If this option is 'for_project', it must be for all measurement
        # types.
        assert not self.for_project or self.all_measurement_types

    def translate(self, value):
        if self.type == 'float':
            return float(value)
        if self.type == 'int':
            return int(value)
        if self.type == 'boolean':
            return bool(value)
        if self.type == 'text':
            return value

        raise ValueError("Unknown Option type: {0}".format(self.type))

    @property
    def all_measurement_types(self):
        return len(self.applies_to_measurement_types) == 0

    def applies_to(self, measurement_type):
        return (
            self.all_measurement_types or
            (measurement_type is not None and
             measurement_type.implementation_slug in
             self.applies_to_measurement_types))

    def applies_to_errors(self, error_config):
        return (self.only_for_error is None or
                error_config is None or
                self.only_for_error in error_config)

    def to_unicode(self, value):
        if self.type == 'boolean':
            return "1" if value else ""
        return unicode(value)

    def default_for(self, organization, measurement_type):
        organization_config, created = (
            models.OrganizationConfig.objects.get_or_create(
                organization=organization,
                measurement_type=measurement_type,
                config_option=self.option, defaults=dict(
                    value=self.default)))

        return self.translate(organization_config.value)


CONFIG_OPTIONS = {
    'use_predefined_locations': Option(
        option='use_predefined_locations',
        short_description='Accepteer alleen voorgedefinieerde locaties',
        long_description=(
            'Hiervoor moet dan een locatie shapefile geüpload worden bij '
            'het toewijzen van activiteiten aan een uitvoerder.'),
        type='boolean',
        default='',
        only_for_error=None,
        for_project=False,
        applies_to_measurement_types=[],
    ),
    'maximum_z1z2_difference': Option(
        option='maximum_z1z2_difference',
        short_description=(
            "Maximale verschil tussen Z1 en Z2 binnen een metingregel (m)"),
        long_description="Absolute waarde, dus altijd positief",
        type="float",
        default='1',
        only_for_error='MET_DIFFERENCE_Z1Z2_MAX_1M',
        for_project=False,
        applies_to_measurement_types=['dwarsprofiel'],
    ),
    'lowest_z_value_allowed': Option(
        option='lowest_z_value_allowed',
        short_description='Laagst toegestane Z1/Z2 waarde (m NAP)',
        long_description=(
            'Een meting in een dwarsprofiel mag niet lager liggen dan dit'),
        type='float',
        default='-10',
        only_for_error='MET_Z_TOO_LOW',
        for_project=False,
        applies_to_measurement_types=['dwarsprofiel'],
    ),
    'maximum_waterway_width': Option(
        option='maximum_waterway_width',
        short_description='Maximale breedte van een waterweg (m)',
        long_description='Dit is de afstand tussen beide oevers (22 codes)',
        type='float',
        default='100',
        only_for_error='MET_WATERWAY_TOO_WIDE',
        for_project=False,
        applies_to_measurement_types=['dwarsprofiel'],
    ),
    'maximum_x_coordinate': Option(
        option='maximum_x_coordinate',
        short_description='Maximum X coordinaat (RD)',
        long_description='In Rijksdriehoek coordinaten',
        type='float',
        default='300000',
        only_for_error=None,
        for_project=True,
        applies_to_measurement_types=[],
    ),
    'minimum_x_coordinate': Option(
        option='minimum_x_coordinate',
        short_description='Minimum X coordinaat (RD)',
        long_description='In Rijksdriehoek coordinaten',
        type='float',
        default='7000',
        only_for_error=None,
        for_project=True,
        applies_to_measurement_types=[],
    ),
    'maximum_y_coordinate': Option(
        option='maximum_y_coordinate',
        short_description='Maximum Y coordinaat (RD)',
        long_description='In Rijksdriehoek coordinaten',
        type='float',
        default='629000',
        only_for_error=None,
        for_project=True,
        applies_to_measurement_types=[],
    ),
    'minimum_y_coordinate': Option(
        option='minimum_y_coordinate',
        short_description='Minimum Y coordinaat (RD)',
        long_description='In Rijksdriehoek coordinaten',
        type='float',
        default='289000',
        only_for_error=None,
        for_project=True,
        applies_to_measurement_types=[],
    ),
    'maximum_location_distance': Option(
        option='maximum_location_distance',
        short_description='Maximum afstand tot geplande meetlocatie, middelpunten (m)',
        long_description='Maximale afstand tussen het middelpung geplande profiel en middelpunt gemeten profiel',
        type='float',
        default='10',
        only_for_error='TOO_FAR_FROM_LOCATION',
        for_project=False,
        applies_to_measurement_types=['dwarsprofiel'],
    ),
    'maximum_location_distance_use_2components': Option(
        option='maximum_location_distance_use_2components',
        short_description='Gebruik nieuwe afstandscontrole',
        long_description='Afstand tussen gepland en gemeten opsplitsen in twee componenten (loodrecht/evenwijdig)',
        type='boolean',
        default='',
        only_for_error=None,
        for_project=False,
        applies_to_measurement_types=['dwarsprofiel'],
    ),
    'maximum_location_distance_parallel': Option(
        option='maximum_location_distance_parallel',
        short_description='Maximum afstand tot geplande meetlocatie, evenwijdig (m)',
        long_description='Maximale afstand evenwijdig tot het geplande profiel',
        type='float',
        default='5',
        only_for_error='TOO_FAR_FROM_LOCATION_PARALLEL',
        for_project=False,
        applies_to_measurement_types=['dwarsprofiel'],
    ),
    'maximum_location_distance_orthogonal': Option(
        option='maximum_location_distance_orthogonal',
        short_description='Maximum afstand tot geplande meetlocatie, loodrecht (m)',
        long_description='Maximale  afstand loodrecht tot het geplande profiel',
        type='float',
        default='5',
        only_for_error='TOO_FAR_FROM_LOCATION_ORTHOGONAL',
        for_project=False,
        applies_to_measurement_types=['dwarsprofiel'],
    ),
    'maximum_mean_distance_between_points': Option(
        option='maximum_mean_distance_between_points',
        short_description=(
            'Maximale gemiddelde afstand tussen profielpunten (m)'),
        long_description='Gemeten tussen beide oevers (de 22 punten)',
        type='float',
        default='2',
        only_for_error='MET_MEAN_MEASUREMENT_DISTANCE',
        for_project=False,
        applies_to_measurement_types=['dwarsprofiel'],
    ),
    'max_measurement_distance': Option(
        option='max_measurement_distance',
        short_description=(
            'Maximale afstand tussen profielpunten (m)'),
        long_description='Zowel binnen de watergang als op de oever',
        type='float',
        default='2.5',
        only_for_error='MET_DISTANCETOOLARGE',
        for_project=False,
        applies_to_measurement_types=['dwarsprofiel'],
    ),
    'hydrovakken_id_field': Option(
        option='hydrovakken_id_field',
        short_description=(
            'Veld dat ID bevat in monstervakken shapefile'),
        long_description=(
            'Daarnaast moeten de shapes bestaan uit lijnen'),
        type='text',
        default='BR_IDENT',
        only_for_error=None,
        for_project=True,
        applies_to_measurement_types=[],
    ),
    'location_id_field': Option(
        option='location_id_field',
        short_description=(
            'Veld dat ID bevat in locatie shapefile'),
        long_description=(
            'Daarnaast moeten de shapes bestaan uit punten'),
        type='text',
        default='ID_DWP',
        only_for_error=None,
        for_project=False,
        applies_to_measurement_types=[],
    ),
    'lowest_below_water_allowed': Option(
        option='lowest_below_water_allowed',
        short_description=(
            'Laagst toegestane Z1/Z2 waarde, gemeten vanaf het waterniveau'),
        long_description=('Altijd een negatief getal'),
        type='float',
        default='-50',
        only_for_error='MET_Z_TOO_LOW_BELOW_WATER',
        for_project=False,
        applies_to_measurement_types=['dwarsprofiel'],
    ),
    'max_distance_to_midline': Option(
        option='max_distance_to_midline',
        short_description=(
            'Maximale afstand van een punt tot aan de middellijn'),
        long_description=(
            'De middellijn is de denkbeeldige lijn die door de 22 codes loopt'
        ),
        type='float',
        default='1',
        only_for_error='MET_DISTANCE_TO_MIDLINE',
        for_project=False,
        applies_to_measurement_types=['dwarsprofiel'],
    ),
    'owner_organisation_eaq_code': Option(
        option='owner_organisation_eaq_code',
        short_description='EAQ code organisatie',
        long_description=(
            'In een RIBX bestand is een kolk eigendom van de eigen '
            'organisatie als deze waarde in het "EAQ" veld staat. Als deze '
            'optie leeg is, zijn alle kolken in eigendom.'),
        type='text',
        default='',
        only_for_error=None,
        for_project=False,
        applies_to_measurement_types=['ribx_reiniging_kolken'],
    ),
    'ignore_drains_with_other_owners': Option(
        option='ignore_drains_with_other_owners',
        short_description='Kolken niet in eigendom negeren',
        long_description=(
            'Als deze optie aan staat, worden kolken die niet in eigendom '
            'zijn niet meegeteld in statistieken en anders getoond op '
            'de kaart.'
            ),
        type='boolean',
        default=False,
        only_for_error=None,
        for_project=False,
        applies_to_measurement_types=['ribx_reiniging_kolken'],
    ),
}


class Configuration(object):
    def __init__(
            self, organization=None, activity=None, project=None,
            measurement_type=None
    ):
        """Give ONE of organization, activity, project. If organization
        is given, measurement_type should be given too."""
        if sum(item is not None for item in (organization,
                                             activity,
                                             project)) != 1:
            raise ValueError(
                "Give either organization, project or activity, not more.")

        self.organization = organization
        self.measurement_type = measurement_type
        self.activity = activity
        self.project = project

    def get(self, config_option):
        option = CONFIG_OPTIONS.get(config_option)

        if self.activity:
            if option.for_project:
                self.project = self.activity.project
                return self.get_project(option)
            else:
                return self.get_activity(option)
        elif self.project:
            return self.get_project(option)
        else:
            return self.get_organization(option)

    def get_organization(self, option):
        measurement_type = (
            None if option.all_measurement_types else self.measurement_type)

        organization_config, created = (
            models.OrganizationConfig.objects.get_or_create(
                organization=self.organization,
                measurement_type=measurement_type,
                config_option=option.option))
        if organization_config.value is None:
            organization_config.value = option.default
            organization_config.save()
        return option.translate(organization_config.value)

    def get_project(self, option):
        project_config, created = (
            models.ProjectConfig.objects.get_or_create(
                project=self.project,
                config_option=option.option))
        if project_config.value is None:
            organization_config, created = (
                models.OrganizationConfig.objects.get_or_create(
                    organization=self.project.organization,
                    measurement_type=None,
                    config_option=option.option))
            if organization_config.value is None:
                organization_config.value = option.default
                organization_config.save()
            project_config.value = organization_config.value
            project_config.save()
        return option.translate(project_config.value)

    def get_activity(self, option):
        activity_config, created = (
            models.ActivityConfig.objects.get_or_create(
                activity=self.activity,
                config_option=option.option))
        if activity_config.value is None:
            measurement_type = (
                None if option.all_measurement_types else
                self.activity.measurement_type)
            organization_config, created = (
                models.OrganizationConfig.objects.get_or_create(
                    organization=self.activity.project.organization,
                    measurement_type=measurement_type,
                    config_option=option.option))
            if organization_config.value is None:
                organization_config.value = option.default
                organization_config.save()
            activity_config.value = organization_config.value
            activity_config.save()
        return option.translate(activity_config.value)

    def set(self, option, value):
        """Save some configuration option to this value, and save it"""
        if self.activity:
            return self.set_activity(option, value)
        elif self.project:
            return self.set_project(option, value)
        else:
            return self.set_organization(option, value)

    def set_activity(self, option, value):
        """Save a configuration option that was set for a project"""
        activity_config, created = models.ActivityConfig.objects.get_or_create(
            activity=self.activity,
            config_option=option.option)
        activity_config.value = option.to_unicode(value)
        activity_config.save()

    def set_project(self, option, value):
        """Save a configuration option that was set for a project"""
        project_config, created = models.ProjectConfig.objects.get_or_create(
            project=self.project,
            config_option=option.option)
        project_config.value = option.to_unicode(value)
        project_config.save()

    def set_organization(self, option, value):
        """Save a configuration option that was set for an organization"""
        measurement_type = (
            None if option.all_measurement_types else self.measurement_type)

        organization_config, created = (
            models.OrganizationConfig.objects.get_or_create(
                organization=self.organization,
                measurement_type=measurement_type,
                config_option=option.option))
        organization_config.value = option.to_unicode(value)
        organization_config.save()

    def options(self):
        """Return only the options that are relevant for this project,
        or activity. Omit options for which the error message is turned off
        anyway."""
        if self.activity:
            measurement_type = self.activity.measurement_type
        elif self.project:
            measurement_type = None
        else:
            measurement_type = self.measurement_type

        error_config = errors.ErrorConfiguration(
            project=self.activity.project if self.activity else self.project,
            organization=self.organization,
            measurement_type=measurement_type)

        want_for_project = self.project is not None

        for (option_key, option) in sorted(CONFIG_OPTIONS.iteritems()):
            if (option.for_project == want_for_project and
                    option.applies_to_errors(error_config) and
                    (self.organization or option.applies_to(
                        measurement_type))):
                yield (option, self.get(option.option))


def get(activity, config_option, project=None):
    """Helper function, this is a common way to use this module."""

    configuration = Configuration(activity=activity, project=project)
    return configuration.get(config_option)
