# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

# Python 3 is coming
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from django.core.urlresolvers import reverse
from django.views.generic import TemplateView

from lizard_ui.views import ViewContextMixin


class TestView(ViewContextMixin, TemplateView):
    """Just renders the ui_base template."""
    template_name = 'lizard_progress/upload_page.html'

    def upload_dialog_url(self):
        """Returns URL to the file upload dialog."""
        return reverse('lizard_progress_uploaddialogview')

    def upload_measurements_url(self):
        """Returns URL to post measurements to."""
        return reverse('lizard_progress_uploadmeasurementsview',
                       kwargs={'project_slug': 'test'})

