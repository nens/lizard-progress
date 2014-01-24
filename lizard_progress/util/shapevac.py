#!/usr/bin/python

"""Utility to find all the shapefile parts in a directory (.shp, .dbf,
etc etc) and put them all into a zipfile of the same name, but the
extensions replaced ("A.shp" goes into "A.zip")."""

import os
import shutil
import sys
import tempfile
import time
import zipfile

from collections import defaultdict

SHAPEFILE_EXTENSIONS = (
    # Source: http://en.wikipedia.org/wiki/Shapefile
    '.shp', '.dbf', '.prj', '.sbx', '.shx', '.sbn', '.sbx', '.sll',
    '.fbn', '.fbx', '.ain', '.aih', '.ixs', '.mxs', '.atx', '.shp.xml',
    '.cpg'
)


def open_zipfile(zipfilepath, mode):
    zipf = zipfile.ZipFile(
        zipfilepath, mode=mode,
        compression=zipfile.ZIP_DEFLATED)

    return zipf


def close_zipfile(zipf):
    zipf.close()


def shapefile_vacuum_directory(directory, verbose=False):
    # Do simple locking using mkdir, then call the real function
    lock_dir = os.path.join(directory, '.lockdir')

    for try_number in range(100):
        try:
            os.mkdir(lock_dir)
        except OSError:
            # Busy waiting, why not...
            time.sleep(0.1)
        else:
            break  # Out of the for loop
    else:
        # Reach last try, fail
        return

    try:
        _shapefile_vacuum_directory(directory, verbose)
    finally:
        try:
            os.rmdir(lock_dir)
        except OSError:
            pass  # ?


def _shapefile_vacuum_directory(directory, verbose=False):
    files_to_add = defaultdict(list)

    for filename in os.listdir(directory):
        if is_shape_part(filename):
            files_to_add[zipfilename(filename)].append(filename)

    for zipname, files in files_to_add.items():
        add_to_zip(directory, zipname, files, verbose)


def is_shape_part(filename):
    return any(
        filename.endswith(extension) for extension in SHAPEFILE_EXTENSIONS)


def zipfilename(filename):
    return os.path.splitext(filename)[0] + ".zip"


def add_to_zip(directory, zipname, files, verbose=False):
    zipfilepath = os.path.join(directory, zipname)

    if os.path.exists(zipfilepath):
        zf = get_zip_file_without(zipfilepath, files)
    else:
        zf = open_zipfile(zipfilepath, mode='a')

    for f in files:
        path = os.path.join(directory, f)
        if verbose:
            notify(path, zipfilepath)
        zf.write(path, f)
        os.remove(path)

    close_zipfile(zf)


def notify(path, zipfilepath):
    print("{}: {}".format(zipfilepath, os.path.basename(path)))


def get_zip_file_without(zipfilepath, files):
    """Extract the existing zipfile to a temp directory, copy
    over all the files not in 'files', remove the temp directory."""
    tempdir = tempfile.mkdtemp()

    zf = open_zipfile(zipfilepath, mode='r')

    for name in zf.namelist():
        if '/' not in name:  # Avoid trickery
            zf.extract(name, tempdir)

    close_zipfile(zf)

    # Write new zip file
    zf = open_zipfile(zipfilepath, mode='w')

    for name in os.listdir(tempdir):
        if name not in files:
            zf.write(os.path.join(tempdir, name), name)

    shutil.rmtree(tempdir)

    return zf


def main():
    args = set(sys.argv[1:])

    if '--help' in args:
        args.remove('--help')
        print(
            "Usage: shapevac [<directory>]. Default is current directory.\n\n"
            "Put all shapefile parts into zipfiles with the same name.")
        sys.exit(0)

    if len(args) == 1:
        directory = args.pop()
    else:
        directory = '.'

    shapefile_vacuum_directory(directory, verbose=True)


if __name__ == '__main__':
    main()
