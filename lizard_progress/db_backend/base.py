# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

"""We use PostGIS and django-transaction-hooks. To do that, we need to
define a custom database backend that inherits from the PostGIS backend
and the transaction-hooks mixin.

The way Django backends work is that they need to be defined as a
DatabaseWrapper class in a base.py module, and then can be configured
using the name of the package (lizard_progress.db_backend, in this
case).

"""

# Python 3 is coming
from __future__ import unicode_literals
from __future__ import absolute_import

from django.contrib.gis.db.backends.postgis import base
from transaction_hooks.mixin import TransactionHooksDatabaseWrapperMixin


class DatabaseWrapper(
        TransactionHooksDatabaseWrapperMixin,
        base.DatabaseWrapper):
    pass
