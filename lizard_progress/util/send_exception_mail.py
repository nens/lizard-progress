# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

"""Function to send a handy traceback to the Servicedesk."""

# Python 3 is coming
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import contextlib
import logging


logger = logging.getLogger(__name__)



def send_exception_mail(where):

    message = ("""
Er is een Exception opgetreden op de Uploadservice, op een plek waar dat
niet hoort en waar een gebruiker er direct last van had. Dit is een
programmeerfout.

Waar: {}

Traceback:
""".format(where))

    logger.exception(message)


@contextlib.contextmanager
def send_email_on_exception(where, reraise=True):
    try:
        yield
    except:
        send_exception_mail(where)

        if reraise:
            # Also re-raise, because the calling code probably also
            # wants to do something in this case, like mark an
            # ExportRun as failed.
            raise
