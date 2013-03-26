# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

"""We have an upload server, maybe we should be able to download too?

Uploaded files can be exported, to one export file per
project/contractor/measurement type combination. These files can be
generated at the press of a button, and downloaded afterwards.

Most measurement types will all use the same exporter, one that
generates a zip file with all the uploaded files. But MET files will
have others: one that creates one big MET file with all the data in
it, and one that generates a file for use in AutoCAD.

See also the models.ExportRun model.
"""

# Python 3 is coming
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import csv
import os
import tempfile
import zipfile

from dxfwrite import DXFEngine as dxf

from metfilelib.util import retrieve_profile
from metfilelib import exporters

from lizard_progress import models
from lizard_progress import tools


def start_run(export_run_id, user):
    """Start the given export run."""
    try:
        export_run = models.ExportRun.objects.get(pk=export_run_id)
    except models.ExportRun.DoesNotExist:
        # Huh?
        return

    export_run.clear()
    export_run.record_start(user)

    if export_run.exporttype == "met":
        export_as_metfile(export_run)
    elif export_run.exporttype == "dxf":
        export_as_dxf(export_run)
    elif export_run.exporttype == "csv":
        export_as_csv(export_run)
    else:
        export_all_files(export_run)
    export_run.set_ready_for_download()


def export_all_files(export_run):
    """Collect all the most recent (non-updated) files, and put them
    in a .zip file."""

    zipfile_path = export_run.export_filename(extension="zip")

    if not os.path.isdir(os.path.dirname(zipfile_path)):
        os.makedirs(os.path.dirname(zipfile_path))

    with zipfile.ZipFile(zipfile_path, 'w') as z:
        for file_path in sorted(export_run.files_to_export()):
            z.write(
                file_path,
                tools.orig_from_unique_filename(os.path.basename(file_path)))

    export_run.file_path = zipfile_path
    export_run.save()


def export_as_metfile(export_run):
    """Export a set of measurements as one combined MET file.

    This works by _retrieving the original <PROFIEL> sections from the
    originally uploaded files_. So no processing is done on them."""

    metfile_path = export_run.export_filename(extension="met")

    if not os.path.isdir(os.path.dirname(metfile_path)):
        os.makedirs(os.path.dirname(metfile_path))

    measurements = export_run.measurements_to_export()

    metfile = retrieve_profile.recreate_metfile([
            (measurement.filename,
             measurement.scheduled.location.location_code)
            for measurement in measurements])

    exporter = exporters.MetfileExporter()

    with open(metfile_path, "w") as f:
        f.write(exporter.export_metfile(metfile))

    export_run.file_path = metfile_path
    export_run.save()


def export_as_dxf(export_run):
    # Get a tmp dir
    temp = tempfile.mkdtemp()

    files = set()
    # For each measurement, create a dxf file
    for measurement in export_run.measurements_to_export():
        file_path = create_dxf(measurement, temp)
        if file_path is not None:
            files.add(file_path)

    zipfile_path = export_run.export_filename(extension="dxf.zip")

    if not os.path.isdir(os.path.dirname(zipfile_path)):
        os.makedirs(os.path.dirname(zipfile_path))

    with zipfile.ZipFile(zipfile_path, 'w') as z:
        for file_path in sorted(files):
            z.write(
                file_path,
                os.path.basename(file_path))
            os.remove(file_path)

    os.rmdir(temp)

    export_run.file_path = zipfile_path
    export_run.save()


def create_dxf(measurement, temp):
    series_id, series_name, profile = retrieve_profile.retrieve(
        measurement.filename,
        measurement.scheduled.location.location_code)

    line = profile.line
    if line is None:
        # No base line. Skip!
        return

    filename = "{id}.dxf".format(
        id=measurement.scheduled.location.location_code)
    filepath = os.path.join(temp, filename)

    drawing = dxf.drawing(filepath)

    x = 0.0
    previous = None
    previous_z1 = None
    previous_z2 = None
    previous_x = None
    for m in profile.sorted_measurements:
        projected_m = line.project(m.point)
        if previous is not None:
            # Add distance between previous and this one to x
            # projected on the line
            p_m = line.project(m.point)
            x += (p_m.subtract(previous)).size

            drawing.add(dxf.line((previous_x, previous_z1),
                                 (x, m.z1),
                                 color=7))
            drawing.add(dxf.line((previous_x, previous_z2),
                                 (x, m.z2),
                                 color=7))
        previous = projected_m
        previous_z1 = m.z1
        previous_z2 = m.z2
        previous_x = x

    drawing.save()
    return filepath


def export_as_csv(export_run):
    # Get a tmp dir
    temp = tempfile.mkdtemp()

    files = set()
    # For each measurement, create a csv file
    for measurement in export_run.measurements_to_export():
        file_path = create_csv(measurement, temp)
        if file_path is not None:
            files.add(file_path)

    zipfile_path = export_run.export_filename(extension="csv.zip")

    if not os.path.isdir(os.path.dirname(zipfile_path)):
        os.makedirs(os.path.dirname(zipfile_path))

    with zipfile.ZipFile(zipfile_path, 'w') as z:
        for file_path in sorted(files):
            z.write(
                file_path,
                os.path.basename(file_path))
            os.remove(file_path)

    os.rmdir(temp)

    export_run.file_path = zipfile_path
    export_run.save()


def create_csv(measurement, temp):
    location_code = measurement.scheduled.location.location_code
    series_id, series_name, profile = retrieve_profile.retrieve(
        measurement.filename,
        location_code)

    base_line = profile.line
    midpoint = profile.midpoint
    if base_line is None or midpoint is None:
        # No base line. Skip!
        return

    filename = "{id}.csv".format(id=location_code)
    filepath = os.path.join(temp, filename)

    with open(filepath, 'w') as f:
        writer = csv.writer(f)
        writer.writerow(["Location:", location_code])
        writer.writerow(["X-coordinaat:", profile.start_x])
        writer.writerow(["Y-coordinaat:", profile.start_y])
        writer.writerow(["Streefpeil:", -999])
        writer.writerow(["Gemeten waterstand:", profile.level_value])
        writer.writerow([])
        writer.writerow([
                "Afstand tot midden (m)",
                "Hoogte (m NAP)",
                "Hoogte zachte bodem (m NAP)"])

        for m in profile.sorted_measurements:
            projected_point = base_line.project(m.point)
            distance = midpoint.subtract(projected_point).size

            # One side has negative numbers
            if base_line.scaled_scalar_projection(m.point) < 0.5:
                distance = -distance

            writer.writerow([
                    "{0:.2f}".format(distance),
                    "{0:.2f}".format(m.z1),
                    "{0:.2f}".format(m.z2)])

    return filepath
