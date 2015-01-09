## Details for the Lizard export, connections to the database tables,
## moving files to ftp servers, etc.

"""Handles export to Lizard. Necessary config is done through
LizardConfiguration objects.

Two things are done:
1) A database table, presumably served by Geoserver, is updated
2) CSV, PNG and DXF files are sent somewhere.

For 1), two things need to be configured:
i) A SqlAlchemy database engine,
e.g. postgresql://almere:password@p-web-map-d6.external-nens.local:5432/almere_test

ii) The table to write to, e.g. almr_dwarsprofielen

For 2), we can send files by FTP or just copy them somewhere. In the
FTP case, set an upload config like:
ftp:ftp.lizardsystem.nl:Flowimages:password:almere/dwarsprofielen/{project_slug}

That is, the string "ftp", follow by server, user, password and
directory. {project_slug} will be filled in by the module.

The file case is simpler: simply file:/path/to/top/directory/{project_slug}

Also, a template for the URL, like
http://ftp.lizardsystem.nl/flowimages/almere/dwarsprofielen/{project_slug}/{filename}
.
This is used for all types of files, and will be filled in in the
database table. {project_slug} and {filename} are filled in.
"""


# Python 3 is coming
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import ftplib
import logging
import os
import shutil

import sqlalchemy
from sqlalchemy.sql import and_

from geoalchemy2 import Geometry
Geometry  # Pyflakes...

logger = logging.getLogger(__name__)


def engine(lizard_config):
    return sqlalchemy.create_engine(lizard_config.geoserver_database_engine)


def table(lizard_config):
    metadata = sqlalchemy.MetaData(bind=engine(lizard_config))
    return sqlalchemy.Table(
        lizard_config.geoserver_table_name, metadata, autoload=True)


def insert(measurement, lizard_config):
    connection = engine(lizard_config).connect()
    the_table = table(lizard_config)
    # If this measurement already exists in the database, we first delete it
    # (easiest way of updating...)
    connection.execute(the_table.delete().where(and_(
        the_table.c.proident == measurement.location.location_code,
        the_table.c.pro_naam == measurement.project.name,
        the_table.c.opdr_nem == measurement.contractor.organization.name)))

    # Now insert the new one
    connection.execute(
        table(lizard_config).insert().values(
            proident=measurement.location.location_code,
            xcoord=measurement.location.the_geom.x,
            ycoord=measurement.location.the_geom.y,
            csv=getattr(measurement, 'csv_url', None),
            graph=getattr(measurement, 'png_url', None),
            dxf=getattr(measurement, 'dxf_url', None),
            pro_naam=measurement.project.name,
            opdr_gev=measurement.project.organization.name,
            opdr_nem=measurement.contractor.organization.name,
            jaar=measurement.date.year,
            datum=measurement.date,
            the_geom=(
                "SRID=28992; " +
                unicode(measurement.location.the_geom))
            ))


def upload(measurement, lizard_config):
    upload_config = lizard_config.upload_config
    url_template = lizard_config.upload_url_template
    project_slug = measurement.location.activity.project.slug

    # Fill in project_slug
    upload_config = upload_config.format(project_slug=project_slug)

    parts = upload_config.split(':')
    uploadtype = parts[0]
    if uploadtype == 'ftp' and len(parts) == 5:
        server, user, password, directories = parts[1:]
        upload_ftp(
            measurement, server, user, password,
            directories, project_slug, url_template)
    elif uploadtype == 'file' and len(parts) == 2:
        directory = parts[1]
        upload_files(measurement, directory, project_slug, url_template)


def upload_ftp(
        measurement, server, user, password, directories,
        project_slug, url_template):
    logger.debug(user)
    logger.debug(password)

    ftp = ftplib.FTP(server, user=user, passwd=password)

    for dirname in directories.split('/'):
        if dirname not in ftp.nlst():
            ftp.mkd(dirname)
        ftp.cwd(dirname)

    # DXF
    if measurement.dxf:
        filename = os.path.basename(measurement.dxf)
        ftp.storbinary(
            b"STOR {filename}".format(filename=filename),
            open(measurement.dxf, "rb"))
        measurement.dxf_url = url_template.format(
            project_slug=project_slug, filename=filename)

    # CSV
    if measurement.csv:
        filename = os.path.basename(measurement.csv)
        ftp.storbinary(
            b"STOR {filename}".format(filename=filename),
            open(measurement.csv, "rb"))
        measurement.csv_url = url_template.format(
            project_slug=project_slug, filename=filename)

    # PNG
    if measurement.png:
        filename = os.path.basename(measurement.png)
        ftp.storbinary(
            b"STOR {filename}".format(filename=filename),
            open(measurement.png, "rb"))
        measurement.png_url = url_template.format(
            project_slug=project_slug, filename=filename)


def upload_files(measurement, directory, project_slug, url_template):
    if not os.path.exists(directory):
        os.makedirs(directory)

    # DXF
    if measurement.dxf:
        filename = os.path.basename(measurement.dxf)
        shutil.copyfile(
            measurement.dxf,
            os.path.join(directory, filename))
        measurement.dxf_url = url_template.format(
            project_slug=project_slug, filename=filename)

    # CSV
    if measurement.csv:
        filename = os.path.basename(measurement.csv)
        shutil.copyfile(
            measurement.csv,
            os.path.join(directory, filename))
        measurement.csv_url = url_template.format(
            project_slug=project_slug, filename=filename)

    # PNG
    if measurement.png:
        filename = os.path.basename(measurement.png)
        shutil.copyfile(
            measurement.png,
            os.path.join(directory, filename))
        measurement.png_url = url_template.format(
            project_slug=project_slug, filename=filename)
