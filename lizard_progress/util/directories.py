# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

"""Helper functions to find out where a given file should be put /
retrieved from."""

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


def mk(directory):
    """Create directory if it doesn't exist yet, then return it."""
    full_path = absolute(directory)
    if not os.path.exists(full_path):
        os.makedirs(full_path)
    return directory


def absolute(path):
    return os.path.join(BASE_DIR, path)


def relative(path):
    return path.replace(BASE_DIR + '/', '')


def project_dir(project):
    """Return base directory for this project."""
    return mk(os.path.join(
        project.organization.name,
        project.slug))


def activity_dir(activity):
    return mk(os.path.join(project_dir(activity.project), str(activity.id)))


def upload_dir(activity):
    return mk(os.path.join(activity_dir(activity), 'uploads'))


def results_dir(activity):
    """Directory where scripts put result files for this actvity."""
    return mk(os.path.join(activity_dir(activity), 'final_results'))


def exports_dir(activity, base_dir=BASE_DIR):
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
        export_dir = mk(export_dir)

    return export_dir


def reports_dir(activity):
    """Directory where uploads put reports from this activity."""
    return mk(os.path.join(activity_dir(activity), 'reports'))


def shapefile_dir(activity):
    """Directory where uploads put shapefiles from this activity."""
    return mk(os.path.join(activity_dir(activity), 'shapefile'))


def location_shapefile_dir(activity):
    """Directory where wizards put location shapefiles activity."""
    return mk(os.path.join(activity_dir(activity), 'locations'))


def location_shapefile_path(activity):
    return os.path.join(
        location_shapefile_dir(activity), b'meetlocaties-{activityid}'.format(
            activityid=activity.id))


def hydrovakken_dir(project):
    """Directory where wizards put hydrovakken shapefiles for this project."""
    return mk(os.path.join(project_dir(project), 'hydrovakken'))


def project_files_dir(project):
    return mk(os.path.join(project_dir(project), 'files'))


def organization_files_dir(organization):
    return mk(os.path.join(organization.name, 'files'))


def files_in(d):
    abs_d = absolute(d)
    for f in os.listdir(abs_d):
        if os.path.isfile(os.path.join(abs_d, f)):
            yield os.path.join(abs_d, f)


def all_files_in(path, extension=None):
    abs_path = absolute(path)
    for directory, dirnames, filenames in os.walk(abs_path):
        for filename in filenames:
            if extension is None or filename.endswith(extension):
                yield os.path.join(directory, filename)


def newest_file_in(path, extension=None):
    mtime = lambda fn: os.stat(os.path.join(absolute(path), fn)).st_mtime
    filenames = sorted(all_files_in(path, extension), key=mtime)
    if filenames:
        return filenames[-1].encode('utf8')
    else:
        return None


def human_size(path):
    size = os.stat(absolute(path)).st_size

    if size < 1000:
        return "{0} bytes".format(size)

    if size < 1000000:
        return "{0:.1f}KB".format(size / 1000)

    return "{0:.1f}MB".format(size / 1000000)
