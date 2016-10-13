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
            expected_attachment = models.ExpectedAttachment.objects.distinct(
                ).get(measurements__location__activity=self.activity,
                      filename__iexact=filename)
        except models.ExpectedAttachment.DoesNotExist:
            return self.error('UNEXPECTED', filename)
        except models.ExpectedAttachment.MultipleObjectsReturned:
            return self.error('QUERY RETURNS MULTIPLE EXPECTED ATTACHMENTS',
                              filename)

        measurements = expected_attachment.register_uploading()
        return self._parser_result(measurements)
