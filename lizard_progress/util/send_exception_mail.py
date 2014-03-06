# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

"""Function to send a handy traceback to the Servicedesk."""

# Python 3 is coming
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import contextlib
import sys
import traceback
import StringIO


from django.core import mail


def send_exception_mail(where, exc_info):
    message = StringIO.StringIO()

    message.write("""\
Er is een Exception opgetreden op de Upload Server, op een plek waar dat
niet hoort en waar een gebruiker er direct last van had. Dit is een
programmeerfout.

Waar: {}

Traceback:
""".format(where))

    traceback.print_exception(*exc_info, limit=None, file=message)

    mail.send_mail(
        "Foutmelding van de Upload Server",
        message.getvalue(),
        "servicedesk@nelen-schuurmans.nl",
        ["remco.gerlich@nelen-schuurmans.nl"])


@contextlib.contextmanager
def send_email_on_exception(where, reraise=True):
    try:
        yield
    except:
        send_exception_mail(where, sys.exc_info())

        if reraise:
            # Also re-raise, because the calling code probably also
            # wants to do something in this case, like mark an
            # ExportRun as failed.
            raise
