from django.test import TestCase

from lizard_progress.views.upload import UploadedFileErrorsView

from lizard_progress.tests.test_models import ContractorF
from lizard_progress.tests.test_models import ProjectF
from lizard_progress.tests.test_models import UploadedFileErrorF
from lizard_progress.tests.test_models import UploadedFileF
from lizard_progress.tests.test_models import UserF


class TestUploadedFileErrorsView(TestCase):
    def test_errors_returns_right_error_lines(self):
        project = ProjectF.create()
        contractor = ContractorF.create(project=project)
        uploaded_by = UserF(username="whee")

        uploaded_file = UploadedFileF.create(
            project=project,
            contractor=contractor,
            uploaded_by=uploaded_by)
        error1 = UploadedFileErrorF.create(
            uploaded_file=uploaded_file, line=2)
        error2 = UploadedFileErrorF.create(
            uploaded_file=uploaded_file, line=1)

        view = UploadedFileErrorsView()
        view.uploaded_file = uploaded_file

        errors = view._errors()
        self.assertEquals(len(errors), 2)
        self.assertEquals(errors[0], error2)
        self.assertEquals(errors[1], error1)
