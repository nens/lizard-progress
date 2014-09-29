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


class Option(namedtuple(
        'Option',
        'option, short_description, long_description,'
        ' type, default, only_for_error')):

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

    def to_unicode(self, value):
        if self.type == 'boolean':
            return "1" if value else ""
        return unicode(value)


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
        ),
    'maximum_z1z2_difference': Option(
        option='maximum_z1z2_difference',
        short_description=(
            "Maximale verschil tussen Z1 en Z2 binnen een metingregel (m)"),
        long_description="Absolute waarde, dus altijd positief",
        type="float",
        default='1',
        only_for_error='MET_DIFFERENCE_Z1Z2_MAX_1M',
        ),
    'lowest_z_value_allowed': Option(
        option='lowest_z_value_allowed',
        short_description='Laagst toegestane Z1/Z2 waarde (m NAP)',
        long_description=(
            'Een meting in een dwarsprofiel mag niet lager liggen dan dit'),
        type='float',
        default='-10',
        only_for_error='MET_Z_TOO_LOW',
        ),
    'maximum_waterway_width': Option(
        option='maximum_waterway_width',
        short_description='Maximale breedte van een waterweg (m)',
        long_description='Dit is de afstand tussen beide oevers (22 codes)',
        type='float',
        default='100',
        only_for_error='MET_WATERWAY_TOO_WIDE',
        ),
    'maximum_x_coordinate': Option(
        option='maximum_x_coordinate',
        short_description='Maximum X coordinaat dwarsprofiel (RD)',
        long_description='In Rijksdriehoek coordinaten',
        type='float',
        default='300000',
        only_for_error='MET_INSIDE_EXTENT',
        ),
    'minimum_x_coordinate': Option(
        option='minimum_x_coordinate',
        short_description='Minimum X coordinaat dwarsprofiel (RD)',
        long_description='In Rijksdriehoek coordinaten',
        type='float',
        default='7000',
        only_for_error='MET_INSIDE_EXTENT',
        ),
    'maximum_y_coordinate': Option(
        option='maximum_y_coordinate',
        short_description='Maximum Y coordinaat dwarsprofiel (RD)',
        long_description='In Rijksdriehoek coordinaten',
        type='float',
        default='629000',
        only_for_error='MET_INSIDE_EXTENT',
        ),
    'minimum_y_coordinate': Option(
        option='minimum_y_coordinate',
        short_description='Minimum Y coordinaat dwarsprofiel (RD)',
        long_description='In Rijksdriehoek coordinaten',
        type='float',
        default='289000',
        only_for_error='MET_INSIDE_EXTENT',
        ),
    'maximum_location_distance': Option(
        option='maximum_location_distance',
        short_description='Maximum afstand tot geplande meetlocatie',
        long_description='In meter',
        type='float',
        default='10',
        only_for_error='TOO_FAR_FROM_LOCATION',
        ),
    'maximum_mean_distance_between_points': Option(
        option='maximum_mean_distance_between_points',
        short_description=(
            'Maximale gemiddelde afstand tussen profielpunten (m)'),
        long_description='Gemeten tussen beide oevers (de 22 punten)',
        type='float',
        default='2',
        only_for_error='MET_MEAN_MEASUREMENT_DISTANCE',
        ),
    'max_measurement_distance': Option(
        option='max_measurement_distance',
        short_description=(
            'Maximale afstand tussen profielpunten (m)'),
        long_description='Zowel binnen de watergang als op de oever',
        type='float',
        default='2.5',
        only_for_error='MET_DISTANCETOOLARGE',
        ),
    'hydrovakken_id_field': Option(
        option='hydrovakken_id_field',
        short_description=(
            'Veld dat ID bevat in hydrovakken shapefile'),
        long_description=(
            'Daarnaast moeten de shapes bestaan uit lijnen'),
        type='text',
        default='BR_IDENT',
        only_for_error=None),
    'location_id_field': Option(
        option='location_id_field',
        short_description=(
            'Veld dat ID bevat in locatie shapefile'),
        long_description=(
            'Daarnaast moeten de shapes bestaan uit punten'),
        type='text',
        default='ID_DWP',
        only_for_error=None),
    'lowest_below_water_allowed': Option(
        option='lowest_below_water_allowed',
        short_description=(
            'Laagst toegestane Z1/Z2 waarde, gemeten vanaf het waterniveau'),
        long_description=('Altijd een negatief getal'),
        type='float',
        default='-50',
        only_for_error='MET_Z_TOO_LOW_BELOW_WATER'),
    'max_distance_to_midline': Option(
        option='max_distance_to_midline',
        short_description=(
            'Maximale afstand van een punt tot aan de middellijn'),
        long_description=(
            'De middellijn is de denkbeeldige lijn die door de 22 codes loopt'
            ),
        type='float',
        default='1',
        only_for_error='MET_DISTANCE_TO_MIDLINE'),
}


class Configuration(object):
    def __init__(self, organization=None, project=None):
        """A Configuration is EITHER for an organization, or a
        project, not both."""
        if (organization and project) or (not organization and not project):
            raise ValueError(
                "Give either organization or project, not both.")

        self.organization = organization
        self.project = project

    def get(self, config_option):
        option = CONFIG_OPTIONS.get(config_option)

        if self.project:
            return self.get_project(option)
        return self.get_organization(option)

    def get_organization(self, option):
        organization_config, created = (
            models.OrganizationConfig.objects.get_or_create(
                organization=self.organization,
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
                    config_option=option.option))
            if organization_config.value is None:
                organization_config.value = option.default
                organization_config.save()
            project_config.value = organization_config.value
            project_config.save()
        return option.translate(project_config.value)

    def set(self, option, value):
        """Save some configuration option to this value, and save it"""
        if self.project:
            return self.set_project(option, value)
        else:
            return self.set_organization(option, value)

    def set_project(self, option, value):
        """Save a configuration option that was set for a project"""
        project_config, created = models.ProjectConfig.objects.get_or_create(
            project=self.project,
            config_option=option.option)
        project_config.value = option.to_unicode(value)
        project_config.save()

    def set_organization(self, option, value):
        """Save a configuration option that was set for an organization"""
        organization_config, created = (
            models.OrganizationConfig.objects.get_or_create(
                organization=self.organization,
                config_option=option.option))
        organization_config.value = option.to_unicode(value)
        organization_config.save()

    def options(self):
        """Return only the options that are relevant for this project,
        omit options for which the error message is turned off
        anyway."""

        error_config = errors.ErrorConfiguration(
            project=self.project,
            organization=self.organization,
            measurement_type=models.AvailableMeasurementType.dwarsprofiel())

        for (option_key, option) in sorted(CONFIG_OPTIONS.iteritems()):
            if (option.only_for_error is None or
                option.only_for_error in error_config):
                    yield (option, self.get(option.option))


def get(project, config_option):
    """Helper function, this is a common way to use this module."""
    configuration = Configuration(project=project)
    return configuration.get(config_option)
