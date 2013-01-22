"""We have a hard disk containing all the files that were
uploaded. Several versions of the same filename may be present (with
different timestamps). Only the newest one should be kept, and it
should be renamed to its actual name."""

import os

from django.core.management.base import BaseCommand
from django.core.management.base import CommandError


def get_timestamp(filename):
    """Check if the filename contains a timestamp; if it does, split
    the filename into a timestamp string and the original filename. If
    it doesn't, return None."""

    # Filenames are of the form 20120822-163552-0-METfile_Oost_WK34.met
    # yyyymmdd-hhmmss-n-filename

    has_timestamp = (
        (len(filename) > 18) and
        (filename[0:8].isdigit()) and
        (filename[8] == '-') and
        (filename[9:15].isdigit()) and
        (filename[15] == '-') and
        (filename[16].isdigit()) and
        (filename[17] == '-'))

    if has_timestamp:
        return (filename[:17], filename[18:])
    else:
        return None


def clean_directory(dirname, filenames):
    orig = dict()  # orig_name: newest_timestamp

    for filename in filenames:
        split = get_timestamp(filename)
        if split is None:
            continue

        timestamp, orig_filename = split

        if orig_filename not in orig or orig[orig_filename] < timestamp:
            orig[orig_filename] = timestamp

    for filename in filenames:
        split = get_timestamp(filename)
        if split is None:
            continue

        timestamp, orig_filename = split

        if timestamp < orig[orig_filename]:
            print("Deleting {0} {1} because it is older than {2}".
                  format(timestamp, orig_filename, orig[orig_filename]))
            os.remove(os.path.join(dirname, filename))
        else:
            print(
                "{0} is not smaller than {1}, renaming."
                .format(timestamp, orig[orig_filename]))
            os.rename(
                os.path.join(dirname, filename),
                os.path.join(dirname, orig_filename))


def walk_split_filenames(start_dir):
    for (dirpath, dirnames, filenames) in os.walk(start_dir):
        for filename in filenames:
            split = get_timestamp(filename)

        if split is None:
            continue

        yield dirpath, filename, split[0], split[1]


class Command(BaseCommand):
    """Go through a directory structure, find all the unique files and
    which to keep. Delete the others, rename the ones we keep."""

    args = "<startdir>"

    def handle(self, *args, **options):
        if not args:
            raise CommandError("No args!")

        start_dir = args[0]
        if not os.path.exists(start_dir) or not os.path.isdir(start_dir):
            raise CommandError("{0} is not a directory.".format(start_dir))

        for (dirpath, dirnames, filenames) in os.walk(start_dir):
            clean_directory(dirpath, filenames)
