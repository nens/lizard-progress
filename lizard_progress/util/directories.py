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
    """Return base directory for this contractor in this project."""
    return mk(os.path.join(
        project_dir(activity.project), str(activity.id)))


def measurement_type_dir(activity, measurement_type):
    """Return base directory for this measurement type in this project
    for this contractor."""
    return mk(os.path.join(
        activity_dir(activity),
        measurement_type.slug))


def make_uploaded_file_path(root, project, contractor,
                            measurement_type, filename):
    """Gives the path to some uploaded file, which depends on the
    project it is for, the contractor that uploaded it and the
    measurement type that got its data from this file.

    Project, contractor, measurement_type can each be either a
    model instance of that type or a string containing the slug
    of one.

    Can be used both for absolute file paths (pass in
    directories.BASE_DIR as root) or for URLs that will be passed to
    Nginx for X-Sendfile (uses /protected/ as the root).

    External URLs should use a reverse() call to the
    lizard_progress_filedownload view instead of this function."""

    project_slug = getattr(project, 'slug', project)
    contractor_slug = getattr(contractor, 'slug', contractor)
    measurement_type_slug = getattr(measurement_type, 'slug', measurement_type)

    return os.path.join(root,
                        project.organization.name,
                        project_slug,
                        contractor_slug,
                        measurement_type_slug,
                        os.path.basename(filename))


def results_dir(activity):
    """Directory where scripts put result files for this contractor in
    this project."""
    return mk(os.path.join(activity_dir(activity), 'final_results'))


def exports_dir(activity):
    """Directory where scripts put result files for this contractor in
    this project."""
    return mk(os.path.join(activity_dir(activity), 'export'))


def reports_dir(activity):
    """Directory where uploads put reports from this contractor in
    this project."""
    return mk(os.path.join(
        activity_dir(activity),
        'reports'))


def shapefile_dir(activity):
    """Directory where uploads put shapefiles from this contractor in
    this project."""
    return mk(os.path.join(activity_dir(activity), 'shapefile'))


def location_shapefile_dir(activity):
    """Directory where wizards put location shapefiles from this
    contractor in this project."""
    return mk(os.path.join(activity_dir(activity), 'locations'))


def location_shapefile_path(activity, available_mtype):
    return os.path.join(
        location_shapefile_dir(activity),
        b'meetlocaties-{mtype}'.format(mtype=available_mtype.slug))


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
