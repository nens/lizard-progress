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

import os
import zipfile

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
