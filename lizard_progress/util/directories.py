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
    if not os.path.exists(directory):
        os.makedirs(directory)
    return directory


def project_dir(project):
    """Return base directory for this project."""
    return mk(os.path.join(
        BASE_DIR,
        project.organization.name,
        project.slug))


def activity_dir(activity):
    return mk(os.path.join(
        project_dir(activity.project), str(activity.id)))


def upload_dir(activity):
    return mk(os.path.join(activity_dir(activity), 'uploads'))


def make_nginx_file_path(activity, full_path):
    """Gives an Nginx internal path to an uploaded file."""

    if full_path and full_path.startswith(upload_dir(activity)):
        return full_path.replace(BASE_DIR, '/protected')


def results_dir(activity):
    """Directory where scripts put result files for this actvity."""
    return mk(os.path.join(activity_dir(activity), 'final_results'))


def exports_dir(activity, base_dir=BASE_DIR):
    """Directory where scripts put result files for this activity. Also
    accessible by the FTP server, therefore in a slightly different
    structure from the other files:

    BASE_DIR/<Organization>/ftp_readonly/<Project>/<Activity id and name>/

    """
    export_dir = os.path.join(
        base_dir, activity.project.organization.name,
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
        location_shapefile_dir(activity),
        b'meetlocaties-{activityid}'.format(
            activityid=activity.id))


def hydrovakken_dir(project):
    """Directory where wizards put hydrovakken shapefiles for this project."""
    return mk(os.path.join(project_dir(project), 'hydrovakken'))


def project_files_dir(project):
    return mk(os.path.join(
        project_dir(project), 'files'))


def organization_files_dir(organization):
    return mk(os.path.join(BASE_DIR, organization.name, 'files'))


def files_in(d):
    for f in os.listdir(d):
        if os.path.isfile(os.path.join(d, f)):
            yield os.path.join(d, f)


def all_files_in(path, extension=None):
    for directory, dirnames, filenames in os.walk(path):
        for filename in filenames:
            if extension is None or filename.endswith(extension):
                yield os.path.join(directory, filename)


def newest_file_in(path, extension=None):
    mtime = lambda fn: os.stat(os.path.join(path, fn)).st_mtime
    filenames = sorted(all_files_in(path, extension), key=mtime)
    if filenames:
        return filenames[-1].encode('utf8')
    else:
        return None


def human_size(path):
    size = os.stat(path).st_size

    if size < 1000:
        return "{0} bytes".format(size)

    if size < 1000000:
        return "{0:.1f}KB".format(size / 1000)

    return "{0:.1f}MB".format(size / 1000000)
