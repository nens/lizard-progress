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
import pkg_resources
import shutil
import tempfile
import zipfile

import shapefile

from metfilelib.util import dxf

from metfilelib.util import retrieve_profile
from metfilelib import exporters

from lizard_progress import errors
from lizard_progress import models
from lizard_progress import lizard_export
from lizard_progress import tools
from lizard_progress import configuration
from lizard_progress.util.send_exception_mail import send_email_on_exception


def start_run(export_run_id, user):
    """Start the given export run."""
    try:
        export_run = models.ExportRun.objects.get(pk=export_run_id)
    except models.ExportRun.DoesNotExist:
        # Huh?
        return

    export_run.clear()
    export_run.record_start(user)

    try:
        with send_email_on_exception(
                "Start export run, id={}".format(export_run.id)):
            if export_run.exporttype == "met":
                export_as_metfile(export_run)
            elif export_run.exporttype == "dxf":
                export_as_dxf(export_run)
            elif export_run.exporttype == "csv":
                export_as_csv(export_run)
            elif export_run.exporttype == "pointshape":
                export_as_shapefile(export_run)
            elif export_run.exporttype == "lizard":
                export_to_lizard(export_run)
            else:
                export_all_files(export_run)
    except:
        # Catch-all except, because this is meant to catch all the
        # exceptions we don't know about yet. The mail is also sent.
        export_run.fail("Onbekende fout, export mislukt")
        return

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
    originally uploaded files_. So no processing is done on them.

    EXCEPT if this is for Almere -- that is, if the organization this
    file belongs to wants to sort its measurements. Or more exactly,
    if this organization checks for the MET_Z1_DIFFERENCE_TOO_LARGE
    error. If it does, we assume they want to sort its measurements
    before exporting them."""

    metfile_path = export_run.export_filename(extension="met")

    if not os.path.isdir(os.path.dirname(metfile_path)):
        os.makedirs(os.path.dirname(metfile_path))

    measurements = export_run.measurements_to_export()

    want_sorted_measurements = errors.ErrorConfiguration(
        project=export_run.activity.project,
        organization=None,  # Give either project or organization
        measurement_type=models.AvailableMeasurementType.dwarsprofiel()
        ).wants_sorted_measurements()

    metfile = retrieve_profile.recreate_metfile([
        (measurement.filename,
         measurement.location.location_code)
        for measurement in measurements])

    exporter = exporters.MetfileExporter(want_sorted_measurements)

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
    retrieved_profile = retrieve_profile.retrieve(
        measurement.filename,
        measurement.location.location_code)

    if retrieved_profile is None:
        raise ValueError("Profile {} not found in file {}".format(
            measurement.location.location_code,
            measurement.filename))

    series_id, series_name, profile = retrieved_profile

    filename = "{id}.dxf".format(
        id=measurement.location.location_code)
    filepath = os.path.join(temp, filename)

    success = dxf.save_as_dxf(profile, filepath)

    return filepath if success else None


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
    location_code = measurement.location.location_code
    series_id, series_name, profile = retrieve_profile.retrieve(
        measurement.filename,
        location_code)

    base_line = profile.line
    midpoint = profile.midpoint
    if base_line is None or midpoint is None:
        # No base line. Skip!
        return

    # Get a tmp dir
    temp = tempfile.mkdtemp()

    filename = "{id}.csv".format(id=location_code)
    filepath = os.path.join(temp, filename)

    with open(filepath, 'w') as f:
        writer = csv.writer(f)
        writer.writerow(["Location:", location_code])
        writer.writerow(["X-coordinaat:", profile.midpoint.x])
        writer.writerow(["Y-coordinaat:", profile.midpoint.y])
        writer.writerow(["Streefpeil:", -999])
        writer.writerow(["Gemeten waterstand:", profile.waterlevel])
        writer.writerow([])
        writer.writerow([
            "Afstand tot midden (m)",
            "Hoogte (m NAP)",
            "Hoogte zachte bodem (m NAP)"])

        for m in profile.sorted_measurements:
            distance = base_line.distance_to_midpoint(m.point)

            writer.writerow([
                "{0:.2f}".format(distance),
                "{0:.2f}".format(m.z1),
                "{0:.2f}".format(m.z2)])

    return filepath


def create_png(measurement, temp):
    from lizard_progress import mtype_specifics
    handler = mtype_specifics.MetfileSpecifics(measurement.location.activity)
    location_code = measurement.location.location_code
    filename = "{id}.png".format(id=location_code)
    filepath = os.path.join(temp, filename)

    handler.image_handler([measurement.location], open(filepath, 'wb'))
    return filepath


def export_to_lizard(export_run):
    """Save measurement data to a Geoserver database table and to
    files on some location that is served by a webserver, so that
    Lizard-wms can show the data."""

    measurements = list(export_run.measurements_to_export())
    # Save CSV and DXF files for those measurements to an FTP server
    # Get a tmp dir
    temp = tempfile.mkdtemp()

    # Create files for the relevant measurements
    for measurement in measurements:
        measurement.dxf = create_dxf(measurement, temp)
        measurement.csv = create_csv(measurement, temp)
        measurement.png = create_png(measurement, temp)
        lizard_export.upload(measurement)

    # Save measurements data to a database table, for Geoserver, including
    # links to the previously saved files
    for measurement in measurements:
        lizard_export.insert(measurement)

    # We don't record a downloadable file, so no need to do anything
    # else, just return
    return


def export_as_shapefile(export_run):
    """Use pyshp to generate a shapefile."""

    locations = list(models.Location.objects.filter(
        activity=export_run.activity,
        the_geom__isnull=False))

    if not locations:
        # Can't generate an empty shapefile.
        export_run.fail("Er zijn 0 locaties, kan geen shapefile genereren.")
        return

    temp_dir = tempfile.mkdtemp()
    filename = export_run.export_filename(extension="")[:-1]  # Remove '.'

    zipfile_path = export_run.export_filename(extension="zip")

    filename = os.path.basename(zipfile_path)[:-4]  # Remove '.zip'
    shape_filepath = os.path.join(temp_dir, filename)

    shp = shapefile.Writer(shapefile.POINT)
    shp.field(
        configuration.get(export_run.activity.project, 'location_id_field')
        .strip().encode('utf8'))
    shp.field(b'X', b'F', 11, 5)
    shp.field(b'Y', b'F', 11, 5)
    shp.field(b'Uploaded', b'L', 1)

    for location in locations:
        shp.point(location.the_geom.x, location.the_geom.y)
        shp.record(
            location.location_code,
            float(location.the_geom.x),
            float(location.the_geom.y),
            location.complete)

    shp.save(shape_filepath)

    # Create ZIP
    if not os.path.isdir(os.path.dirname(zipfile_path)):
        os.makedirs(os.path.dirname(zipfile_path))

    with zipfile.ZipFile(zipfile_path, 'w') as z:
        for file_path in os.listdir(temp_dir):
            z.write(os.path.join(temp_dir, file_path), file_path)
        # Add a .prj too, if we can find it
        prj = pkg_resources.resource_filename(
            'lizard_progress', 'rijksdriehoek.prj')
        if prj and os.path.exists(prj):
            z.write(prj, filename + ".prj")

    shutil.rmtree(temp_dir)

    export_run.file_path = zipfile_path
    export_run.save()
