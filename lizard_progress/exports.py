# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

"""We have an upload service, maybe we should be able to download too?

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

from lxml import etree
import shapefile

from metfilelib.util import dxf
from metfilelib.util import retrieve_profile
from metfilelib import exporters
from lizard_progress import errors
from lizard_progress import models
from lizard_progress import lizard_export
from lizard_progress import configuration

import logging

logger = logging.getLogger(__name__)


def open_zipfile(zipfile_path):
    """Function to open a Zip file, so that we do it the same way each time."""

    # allowZip64=True is needed so that we can create files larger
    # than 2GB.
    return zipfile.ZipFile(
        zipfile_path, 'w', compression=zipfile.ZIP_DEFLATED, allowZip64=True)


def start_run(export_run_id, user):
    """Start the given export run."""
    try:
        export_run = models.ExportRun.objects.get(pk=export_run_id)
    except models.ExportRun.DoesNotExist:
        logger.error('This point should have never been reached.')
        # Huh?
        return

    export_run.clear()
    export_run.record_start(user)

    try:
        if export_run.exporttype == "met":
            export_as_metfile(export_run)
        elif export_run.exporttype == "dxf":
            export_as_dxf(export_run)
        elif export_run.exporttype == "csv":
            export_as_csv(export_run)
        elif export_run.exporttype == "pointshape":
            export_as_shapefile(export_run, 'point')
        elif export_run.exporttype == "drainshape":
            export_as_shapefile(export_run, 'drain')
        elif export_run.exporttype == "manholeshape":
            export_as_shapefile(export_run, 'manhole')
        elif export_run.exporttype == "pipeshape":
            export_as_shapefile(export_run, 'pipe')
        elif export_run.exporttype == "lizard":
            export_to_lizard(export_run)
        elif export_run.exporttype == models.DIRECTORY_SYNC_TYPE:
            export_all_files_to_directory(export_run)
        elif export_run.exporttype == 'mergeribx':
            export_mergeribx(export_run)
        else:
            export_all_files(export_run)
    except:
        logger.exception('Fout in export run met id: %s', str(export_run.id))
        # Catch-all except, because this is meant to catch all the
        # exceptions we don't know about yet. The mail is also sent.
        export_run.fail("Onbekende fout, export mislukt")
        return

    export_run.set_ready_for_download()


def export_all_files(export_run):
    """Collect all the most recent (non-updated) files, and put them
    in a .zip file."""

    zipfile_path = export_run.abs_export_filename(extension="zip")

    if not os.path.isdir(os.path.dirname(zipfile_path)):
        os.makedirs(os.path.dirname(zipfile_path))

    logger.debug(zipfile_path)

    with open_zipfile(zipfile_path) as z:
        for file_path in sorted(export_run.abs_files_to_export()):
            logger.debug("Files to add to zipfile: " + str(file_path))
            z.write(file_path, os.path.basename(file_path))

    export_run.rel_file_path = zipfile_path
    # ^^ absolute path is converted to relative path in the model's save method
    export_run.save()


def _is_activity(tag):
    """Check if Ribx tag is an 'activity'."""
    return tag.startswith('ZB_')


def merge_ribx(ribx_files):
    """Merge ribx files into one ElementTree.

    Args:
        ribx_files: a list of ribx file paths

    Returns:
        a tuple: (lxml.etree.ElementTree, error_msg). If no merged Ribx can
        be produced the ElementTree is None and the error_msg will contain
        the reason.
    """
    xml_element_tree = None
    for ribxfile in ribx_files:
        data = etree.parse(ribxfile).getroot()
        for elem in data.getchildren():
            if xml_element_tree is None:
                xml_element_tree = data  # Set root with initial data

                # Check some mandatory tags
                try:
                    language = data.xpath('/*/*/A2')[0]
                    ribx_version = data.xpath('/*/*/A6')[0]
                    logger.debug("A2: %s, A6: %s", language, ribx_version)
                except IndexError:
                    logger.exception("No A2 or A6 tag in Ribx.")
                    return (None, "Geen A2 of A6 tag in Ribx")
            else:
                if _is_activity(elem.tag):
                    xml_element_tree.append(elem)
    if not xml_element_tree:
        return (None, "Geen Ribx bestanden gevonden.")
    return (etree.ElementTree(xml_element_tree), "")


def export_mergeribx(export_run):
    ribx_files = [f for f in export_run.abs_files_to_export() if
                  f.endswith('ribx')]
    merged_ribx, error_msg = merge_ribx(ribx_files)

    if not merged_ribx:
        export_run.fail(error_msg)
        return

    merged_ribx_path = export_run.abs_export_filename(extension="ribx")
    if not os.path.isdir(os.path.dirname(merged_ribx_path)):
        os.makedirs(os.path.dirname(merged_ribx_path))

    with open(merged_ribx_path, 'w') as output:
            xml_string = etree.tostring(merged_ribx, xml_declaration=True,
                                        encoding=merged_ribx.docinfo.encoding)
            output.write(xml_string)

    export_run.rel_file_path = merged_ribx_path
    # ^^ absolute path is converted to relative path in the model's save method
    export_run.save()


def export_all_files_to_directory(export_run):
    """Collect all the most recent (non-updated) files, and put them
    in a directory."""

    directory = export_run.abs_export_dirname()
    logger.info("Exporting/updating files in %s", directory)

    if not os.path.isdir(directory):
        os.makedirs(directory)
        logger.info("Created directory %s", directory)

    num_added = 0
    num_updated = 0
    # TODO: do we need to delete files?
    for source in sorted(export_run.abs_files_to_export()):
        filename = os.path.basename(source)
        target = os.path.join(directory, filename)
        if not os.path.exists(target):
            shutil.copyfile(source, target)
            logger.debug("Copied new file to %s", target)
            num_added += 1
        else:
            # File exists, check if it needs updating.
            source_mtime = os.path.getmtime(source)
            target_mtime = os.path.getmtime(target)
            if source_mtime > target_mtime:
                shutil.copyfile(source, target)
                logger.debug("Updated file %s", target)
                num_updated += 1
            else:
                logger.debug("File %s didn't need updating", target)

    logger.info("Added %s files and updated %s files in %s",
                num_added, num_updated, directory)
    export_run.rel_file_path = directory
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

    metfile_path = export_run.abs_export_filename(extension="met")

    if not os.path.isdir(os.path.dirname(metfile_path)):
        os.makedirs(os.path.dirname(metfile_path))

    measurements = export_run.measurements_to_export()

    want_sorted_measurements = errors.ErrorConfiguration(
        project=export_run.activity.project,
        organization=None,  # Give either project or organization
        measurement_type=models.AvailableMeasurementType.dwarsprofiel()
    ).wants_sorted_measurements()

    metfile = retrieve_profile.recreate_metfile([
        (measurement.abs_file_path, measurement.location.location_code)
        for measurement in measurements
    ])

    exporter = exporters.MetfileExporter(want_sorted_measurements)

    with open(metfile_path, "w") as f:
        f.write(exporter.export_metfile(metfile))

    export_run.rel_file_path = metfile_path
    # ^^ absolute path is converted to relative path in the model's save method
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

    zipfile_path = export_run.abs_export_filename(extension="dxf.zip")

    if not os.path.isdir(os.path.dirname(zipfile_path)):
        os.makedirs(os.path.dirname(zipfile_path))

    with open_zipfile(zipfile_path) as z:
        for file_path in sorted(files):
            z.write(
                file_path,
                os.path.basename(file_path))
            os.remove(file_path)

    os.rmdir(temp)

    export_run.rel_file_path = zipfile_path
    # ^^ absolute path is converted to relative path in the model's save method
    export_run.save()


def create_dxf(measurement, temp):
    retrieved_profile = retrieve_profile.retrieve(
        measurement.abs_file_path, measurement.location.location_code
    )

    if retrieved_profile is None:
        raise ValueError("Profile {} not found in file {}".format(
            measurement.location.location_code,
            measurement.abs_file_path))

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

    zipfile_path = export_run.abs_export_filename(extension="csv.zip")

    if not os.path.isdir(os.path.dirname(zipfile_path)):
        os.makedirs(os.path.dirname(zipfile_path))

    with open_zipfile(zipfile_path) as z:
        for file_path in sorted(files):
            z.write(
                file_path,
                os.path.basename(file_path))
            os.remove(file_path)

    os.rmdir(temp)

    export_run.rel_file_path = zipfile_path
    # ^^ absolute path is converted to relative path in the model's save method
    export_run.save()


def create_csv(measurement, temp):
    location_code = measurement.location.location_code
    series_id, series_name, profile = retrieve_profile.retrieve(
        measurement.abs_file_path, location_code
    )

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

    lizard_config = export_run.activity.project.organization.lizard_config

    measurements = list(export_run.measurements_to_export())
    # Save CSV and DXF files for those measurements to an FTP server
    # Get a tmp dir
    temp = tempfile.mkdtemp()

    # Create files for the relevant measurements
    for measurement in measurements:
        measurement.dxf = create_dxf(measurement, temp)
        measurement.csv = create_csv(measurement, temp)
        measurement.png = create_png(measurement, temp)
        lizard_export.upload(measurement, lizard_config)

    # Save measurements data to a database table, for Geoserver, including
    # links to the previously saved files
    for measurement in measurements:
        lizard_export.insert(measurement, lizard_config)

    # We don't record a downloadable file, so no need to do anything
    # else, just return
    return


def export_as_shapefile(export_run, location_type):
    """Use pyshp to generate a shapefile."""

    locations = list(models.Location.objects.filter(
        activity=export_run.activity,
        the_geom__isnull=False,
        location_type=location_type,
        not_part_of_project=False))

    if not locations:
        # Can't generate an empty shapefile.
        export_run.fail("Er zijn 0 locaties, kan geen shapefile genereren.")
        return

    if location_type == 'point':
        fieldname = configuration.get(
            export_run.activity, 'location_id_field'
        ).strip().encode('utf8')
    else:
        fieldname = b'Ref'

    is_point = locations[0].is_point
    add_planning = export_run.activity.specifics().allow_planning_dates

    temp_dir = tempfile.mkdtemp()

    zipfile_path = export_run.abs_export_filename(extension="zip")

    filename = os.path.basename(zipfile_path)[:-4]  # Remove '.zip'

    if is_point:
        export_locations_as_points(
            export_run, temp_dir, filename, zipfile_path, locations, fieldname,
            add_planning)
    else:
        export_locations_as_lines(
            export_run, temp_dir, filename, zipfile_path, locations, fieldname,
            add_planning)

    export_run.rel_file_path = zipfile_path
    # ^^ absolute path is converted to relative path in the model's save method
    export_run.save()


def export_locations_as_points(
        export_run, temp_dir, filename, zipfile_path, locations, fieldname,
        add_planning):
    shape_filepath = os.path.join(temp_dir, filename).encode('utf8')
    shp = shapefile.Writer(shapefile.POINT)
    shp.field(fieldname)
    shp.field(b'X', b'F', 11, 5)
    shp.field(b'Y', b'F', 11, 5)
    shp.field(b'Complete', b'L', 1)
    if add_planning:
        shp.field(b'Jaar', b'C', 4)
        shp.field(b'Weeknummer', b'C', 2)
        shp.field(b'Dagnummer', b'C', 1)

    for location in locations:
        shp.point(location.the_geom.x, location.the_geom.y)
        record = [location.location_code.encode('utf8'),
                  float(location.the_geom.x),
                  float(location.the_geom.y),
                  location.complete]

        if add_planning:
            if location.planned_date:
                record.extend(
                    [str(w) for w in location.planned_date.isocalendar()])
            else:
                record.extend([b'    ', b'  ', b' '])
        shp.record(*record)

    shp.save(shape_filepath)

    # Create ZIP
    if not os.path.isdir(os.path.dirname(zipfile_path)):
        os.makedirs(os.path.dirname(zipfile_path))

    with open_zipfile(zipfile_path) as z:
        for file_path in os.listdir(temp_dir):
            z.write(os.path.join(temp_dir, file_path), file_path)
        # Add a .prj too, if we can find it
        prj = pkg_resources.resource_filename(
            'lizard_progress', 'rijksdriehoek.prj')
        if prj and os.path.exists(prj):
            z.write(prj, filename + ".prj")

    shutil.rmtree(temp_dir)


def export_locations_as_lines(
        export_run, temp_dir, filename, zipfile_path, locations, fieldname,
        add_planning):
    shape_filepath = os.path.join(temp_dir, filename)
    shp = shapefile.Writer(shapefile.POLYLINE)
    shp.field(fieldname)
    shp.field(b'Lengte (m)')
    shp.field(b'Compleet', b'L', 1)

    if add_planning:
        shp.field(b'Jaar', b'C', 4)
        shp.field(b'Weeknummer', b'C', 2)
        shp.field(b'Dagnummer', b'C', 1)

    for location in locations:
        line = [list(c) for c in location.the_geom.coords]
        shp.poly([line])
        record = [
            location.location_code.encode('utf8'),
            round(location.the_geom.length, 2),
            location.complete]

        if add_planning:
            if location.planned_date:
                record.extend(
                    [str(w) for w in location.planned_date.isocalendar()])
            else:
                record.extend([b'    ', b'  ', b' '])
        shp.record(*record)

    shp.save(shape_filepath)

    # Create ZIP
    if not os.path.isdir(os.path.dirname(zipfile_path)):
        os.makedirs(os.path.dirname(zipfile_path))

    with open_zipfile(zipfile_path) as z:
        for file_path in os.listdir(temp_dir):
            z.write(os.path.join(temp_dir, file_path), file_path)
        # Add a .prj too, if we can find it
        prj = pkg_resources.resource_filename(
            'lizard_progress', 'rijksdriehoek.prj')
        if prj and os.path.exists(prj):
            z.write(prj, filename + ".prj")

    shutil.rmtree(temp_dir)
