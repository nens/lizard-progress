FROM ubuntu:trusty

MAINTAINER Reinout <reinout.vanrees@nelen-schuurmans.nl>

# Change the date to force rebuilding the whole image
ENV REFRESHED_AT 1972-12-25

# Update the packages
RUN apt-get update && apt-get upgrade -y

# system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gettext \
    git \
    libjpeg-dev \
    libxml2-dev \
    libxslt-dev \
    postgresql-client \
    python-dev \
    python-gdal \
    python-mapnik \
    python-matplotlib \
    python-nose \
    python-pip \
    python-psycopg2 \
    python-tornado \
    zlib1g-dev \
&& apt-get clean -y

RUN pip install --upgrade pip setuptools
RUN pip install zc.buildout

VOLUME /code
WORKDIR /code
