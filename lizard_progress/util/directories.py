# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

"""
Helper functions to find out where a given file should be put / retrieved from.

paths can be relative or absolute (indicated by 'rel_', or 'abs_' prefix
respectively)
"""

# Python 3 is coming
from __future__ import division

import os

from django.conf import settings


BASE_DIR = getattr(
    settings,
    'LIZARD_PROGRESS_ROOT',
    os.path.join(settings.BUILDOUT_DIR, 'var', 'lizard_progress'))


def clean(s):
    """Remove characters that aren't allowed in filenames."""
    for char in """*."/\\[]:;|=,\x00""":
        s = s.replace(char, '')
    return s


def mk_abs(directory):
    """Create directory if it doesn't exist yet, then return it."""
    full_path = absolute(directory)
    if not os.path.exists(full_path):
        os.makedirs(full_path)
    return full_path


def mk_rel(directory):
    """Create directory if it doesn't exist yet, then return it."""
    full_path = absolute(directory)
    if not os.path.exists(full_path):
        os.makedirs(full_path)
    return directory


def absolute(path):
    if not path.startswith('/'):
        return os.path.join(BASE_DIR, path)
    return path


def relative(path):
    return path.replace(BASE_DIR + '/', '')


def rel_project_dir(project):
    """Return base directory for this project."""
    return mk_rel(os.path.join(
        project.organization.name,
        project.slug))


def rel_activity_dir(activity):
    return mk_rel(
        os.path.join(rel_project_dir(activity.project), str(activity.id)))


def abs_upload_dir(activity):
    return mk_abs(os.path.join(rel_activity_dir(activity), 'uploads'))


def abs_results_dir(activity):
    """Directory where scripts put result files for this actvity."""
    return mk_abs(os.path.join(rel_activity_dir(activity), 'final_results'))


def abs_exports_dir(activity, base_dir=BASE_DIR):
    """Directory where scripts put result files for this activity. Also
    accessible by the FTP server, therefore in a slightly different
    structure from the other files:

    <Organization>/ftp_readonly/<Project>/<Activity id and name>/
    """
    export_dir = os.path.join(
        activity.project.organization.name,
        'ftp_readonly', activity.project.slug,
        '{} - {}'.format(activity.id, clean(activity.name)))

    if base_dir.startswith(settings.BUILDOUT_DIR):
        export_dir = mk_abs(export_dir)

    return export_dir


def abs_reports_dir(activity):
    """Directory where uploads put reports from this activity."""
    return mk_abs(os.path.join(rel_activity_dir(activity), 'reports'))


def abs_shapefile_dir(activity):
    """Directory where uploads put shapefiles from this activity."""
    return mk_abs(os.path.join(rel_activity_dir(activity), 'shapefile'))


def abs_location_shapefile_dir(activity):
    """Directory where wizards put location shapefiles activity."""
    return mk_abs(os.path.join(rel_activity_dir(activity), 'locations'))


def abs_location_shapefile_path(activity):
    return os.path.join(
        abs_location_shapefile_dir(activity),
        b'meetlocaties-{activityid}'.format(activityid=activity.id)
    )


def abs_hydrovakken_dir(project):
    """Directory where wizards put hydrovakken shapefiles for this project."""
    return mk_abs(os.path.join(rel_project_dir(project), 'hydrovakken'))


def abs_project_files_dir(project):
    return mk_abs(os.path.join(rel_project_dir(project), 'files'))


def abs_organization_files_dir(organization):
    return mk_abs(os.path.join(organization.name, 'files'))


def abs_files_in(abs_dir):
    for f in os.listdir(abs_dir):
        if os.path.isfile(os.path.join(abs_dir, f)):
            yield os.path.join(abs_dir, f)


def all_abs_files_in(abs_path, extension=None):
    abs_path = absolute(abs_path)
    for directory, dirnames, filenames in os.walk(abs_path):
        for filename in filenames:
            if extension is None or filename.endswith(extension):
                yield os.path.join(directory, filename)


def human_size(abs_path):
    size = os.stat(abs_path).st_size

    if size < 1000:
        return "{0} bytes".format(size)

    if size < 1000000:
        return "{0:.1f}KB".format(size / 1000)

    return "{0:.1f}MB".format(size / 1000000)
