## Details for the Lizard export, connections to the database tables,
## moving files to ftp servers, etc.

# Python 3 is coming
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import ftplib
import logging
import os

import sqlalchemy

from geoalchemy2 import Geometry
Geometry  # Pyflakes...

logger = logging.getLogger(__name__)


def engine(lizard_config):
    return sqlalchemy.create_engine(lizard_config.geoserver_database_engine)


def table(lizard_config):
    metadata = sqlalchemy.MetaData(bind=engine(lizard_config))
    return sqlalchemy.Table(
        lizard_config.geoserver_table_name, metadata, autoload=True)


def existing_profiles(lizard_config):
    t = table(lizard_config)
    conn = engine(lizard_config).connect()

    return set(
        (row['pro_naam'], row['opdr_nem'], row['proident'])
        for row in conn.execute(t.select()))


def insert(measurement):
    lizard_config = measurement.scheduled.project.organization.lizard_config
    engine(lizard_config).connect().execute(
        table(lizard_config).insert().values(
            proident=measurement.scheduled.location.location_code,
            xcoord=measurement.scheduled.location.the_geom.x,
            ycoord=measurement.scheduled.location.the_geom.y,
            csv=getattr(measurement, 'csv_url', None),
            graph=getattr(measurement, 'png_url', None),
            dxf=getattr(measurement, 'dxf_url', None),
            pro_naam=measurement.scheduled.project.name,
            opdr_gev=measurement.scheduled.project.organization.name,
            opdr_nem=measurement.scheduled.contractor.organization.name,
            jaar=measurement.date.year,
            datum=measurement.date,
            the_geom=(
                "SRID=28992; " +
                unicode(measurement.scheduled.location.the_geom))
            ))


def upload(measurement):
    lizard_config = measurement.scheduled.project.organization.lizard_config
    upload_config = lizard_config.upload_config
    url_template = lizard_config.upload_url_template
    project_slug = measurement.scheduled.project.slug
    upload_config = upload_config.format(project_slug=project_slug)

    parts = upload_config.split(':')
    if len(parts) != 5:
        # Don't know what to do
        return

    uploadtype, server, user, password, directories = parts
    logger.debug(user)
    logger.debug(password)

    if uploadtype != 'ftp':
        return

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
