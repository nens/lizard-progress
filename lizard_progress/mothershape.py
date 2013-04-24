import os
import osgeo.ogr
import sys

from django.template.loader import get_template
from django.template import Context
from lizard_progress import models


def check_mothershape(project, contractor, shape_path, report_file):
    """Given a path, output a report to 'report_file'. Report_file may
    be equal to sys.stdout for testing purposes."""

    shapefile = osgeo.ogr.Open(shape_path)
    layer = shapefile.GetLayer(0)

    errors = []

    if layer.GetFeatureCount() == 0:
        report_file.write("Geen features gevonden.")
        return

    if layer.GetFeature(0).GetField(b"MONSTERVAK") is None:
        report_file.write(
            "Veld 'monstervak' niet aangetroffen in de shape, "
            "geen controle uitgevoerd.")
        return

    for feature_num in range(layer.GetFeatureCount()):
        feature = layer.GetFeature(feature_num)
        location_code = feature.GetField(b"MONSTERVAK")

        if not location_code:
            # Skip? I guess
            continue

        errordict = {
            'code': location_code,
            'errors': []
            }

        try:
            location = models.Location.objects.get(
                project=project, location_code=location_code)
            try:
                measurement = models.Measurement.objects.get(
                    scheduled__location=location,
                    scheduled__contractor=contractor,
                    scheduled__project=project)
                for what, data in measurement.data.items():
                    what = what.upper()
                    try:
                        filled_in = feature.GetField(what.encode('utf8'))
                        if unicode(filled_in) != data['amount']:
                            errordict['errors'].append(
                                ("Hydrovak {hydrovak}, meetwaarde voor"
                                 " {what}: {shape} in shape is ongelijk"
                                 " aan {csv} in CSV\n").
                                format(
                                    hydrovak=location_code,
                                    what=what,
                                    shape=filled_in,
                                    csv=data['amount']))
                    except ValueError:
                        errordict['errors'].append(
                            ("Veld niet gevonden: meetwaarde voor "
                             "{what} bij hydrovak {hydrovak}.\n").
                            format(
                                what=what,
                                hydrovak=location_code))
            except models.Measurement.DoesNotExist:
                errordict['errors'].append(
                    ("Laboratoriumdata voor hydrovak {0} niet gevonden "
                     "in de database. Geen CSV file aanwezig?")
                    .format(location_code))
        except models.Location.DoesNotExist:
            errordict['errors'].append(
                ("Hydrovak {0} niet gevonden "
                 "in de database. Geen CSV file aanwezig?")
                .format(location_code))

        if errordict['errors']:
            errors.append(errordict)

    t = get_template("lizard_progress/moedershape_testrapport.txt")
    report_file.write(t.render(Context({
                    'erratic_locations': errors,
                    'shapefilename': os.path.basename(shape_path),
                })))


def test():
    check_mothershape(
        models.Project.objects.get(pk=3),
        ('/home/remcogerlich/src/git/lizard-progress/Data Frederik/'
         'Aanlevering opdrachtnemer/Polder_Bornepas_incl_meerwerk.shp'),
        sys.stdout)
