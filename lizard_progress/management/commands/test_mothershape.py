# -*- coding: utf-8 -*-
# Copyright 2011 Nelen & Schuurmans
from __future__ import division

from django.core.management.base import BaseCommand

from lizard_progress import mothershape

import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    args = ""
    help = "TODO"

    def handle(self, *args, **options):
        mothershape.test()
