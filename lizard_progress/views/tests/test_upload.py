from lizard_progress.views.upload import UploadedFileErrorsView
from lizard_progress.tests.base import FixturesTestCase
from lizard_progress.tests.test_models import ActivityF
from lizard_progress.tests.test_models import UploadedFileErrorF
from lizard_progress.tests.test_models import UploadedFileF
from lizard_progress.tests.test_models import UserF


class TestUploadedFileErrorsView(FixturesTestCase):
    def test_errors_returns_right_error_lines(self):
        activity = ActivityF.create()

        uploaded_by = UserF(username="whee")

        uploaded_file = UploadedFileF.create(
            activity=activity,
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
