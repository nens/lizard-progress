"""Soms heeft Erik een shapefile met IDs erin, en wil hij X/Y
coordinaten van die IDs hebben.

Stappen:
- De .db openen in OO / Excel, opslaan als CSV (komma gescheiden)
- Dit script aanroepen met als argumenten:
  - De kolom waarin het ID veld staat (meest linker is 1)
  - De filename van de .csv.

Daarna print het script een lijst met IDs met bijbehorende X/Y in
rijksdriehoek, gevonden in het dwarsprofielen project."""

import csv
import os

from django.core.management.base import BaseCommand, CommandError

from lizard_progress import models


class Command(BaseCommand):
    args = '<colnr> <filename>'
    help = 'Print Rijksdriehoek coordinaten van IDs in Dwarsprofielen.'

    def handle(self, *args, **options):
        if len(args) != 2:
            raise CommandError("Command needs 2 arguments.")
        try:
            colnr = int(args[0])
            colnr -= 1  # So we can count from 0
        except (TypeError, ValueError):
            raise CommandError("First argument should be an int.")

        filename = args[1]
        if not os.path.exists(filename):
            raise CommandError("File '{0}' does not exist.".format(filename))

        project = models.Project.objects.get(pk=1)  # Dwarsprofielen

        csvfile = csv.reader(open(filename))
        for row in csvfile:
            item = row[colnr]

            # Hysterical raisins...
            if item.count('_') == 0:
                item = "{0}-{1}_{2}".format(*item.split('-'))

            try:
                location = models.Location.objects.get(
                    location_code=item, project=project)
                print(u','.join(
                        (location.location_code,
                         unicode(location.the_geom.x),
                         unicode(location.the_geom.y))))
            except models.Location.DoesNotExist:
                print("Item {0} not found!".format(item))
