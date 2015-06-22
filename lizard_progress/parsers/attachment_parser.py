import os

from lizard_progress import specifics

from lizard_progress import models


class ExpectedAttachmentParser(specifics.ProgressParser):
    """Parser for any uploaded files that have previously been marked as
    'expected' (e.g., by being mentioned in a RIBX file for some
    location)"""

    FILE_TYPE = specifics.FILE_PATH  # Just receive a path in self.file_object

    ERRORS = {
        'UNEXPECTED': 'Onverwacht bestand: %s',
    }

    def parse(self, check_only=False):
        filename = os.path.basename(self.file_object)

        try:
            expected_attachment = models.ExpectedAttachment.objects.get(
                measurement__location__activity=self.activity,
                filename=filename)
        except models.ExpectedAttachment.DoesNotExist:
            return self.error('UNEXPECTED', filename)

        expected_attachment.uploaded = True
        expected_attachment.save()

        measurements = []
        for measurement in expected_attachment.measurement_set.all(
                ).select_related():
            location = measurement.location
            new_measurement = models.Measurement.objects.create(
                location=location,
                date=None,
                parent=measurement,
                data={'filetype': 'media'},
                the_geom=None)
            measurements.append(new_measurement)
            if location.all_expected_attachments_present:
                location.complete = True
                location.save()

        return self._parser_result(measurements)
