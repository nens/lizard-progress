# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

"""Helper functions for cross section (dwarsprofiel) graphs."""

# Python 3 is coming
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division


import colorsys
import itertools
import math
from fractions import Fraction

from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from metfilelib.util.linear_algebra import Line, Point

from lizard_progress import models


class PlottingData:
    """
    Class attributes:

        - data
        - baseline
        - left
        - right
        - waterlevel
        - distances
        - tops
        - bottoms
        - location
        - date
    """

    def __init__(self, data, location, date):
        self.location = location
        self.date = date

        self.title = (
            'Dwarsprofiel {code}, werkzaamheid {activity}, {date}'
            .format(code=location.location_code,
                    activity=location.activity,
                    date=date.strftime("%d/%m/%y")))

        (self.baseline, self.left,
         self.right, self.waterlevel) = self.find_base_line(data)

        self.data = self.sort_data(data, self.baseline)

        self.distances, self.tops, self.bottoms = [], [], []
        for measurement in self.data:
            x = float(measurement['x'])
            y = float(measurement['y'])

            self.distances.append(
                self.baseline.distance_to_midpoint(Point(x=x, y=y)))
            self.tops.append(float(measurement['top']))
            self.bottoms.append(float(measurement['bottom']))

    @property
    def project(self):
        return self.location.activity.project

    @staticmethod
    def sort_data(data, baseline):
        data = list(data)
        data.sort(
            key=lambda d: baseline.distance_to_midpoint(Point(d['x'], d['y'])))
        return data

    @staticmethod
    def find_base_line(data):
        codes_22 = [d for d in data
                    if d['type'] == '22']

        if len(codes_22) == 2:
            p1 = codes_22[0]
            p2 = codes_22[1]
        else:
            # It's hopeless if they aren't there, do something
            p1 = data[0]
            p2 = data[-1]

        left = Point(x=p1['x'], y=p1['y'])
        right = Point(x=p2['x'], y=p2['y'])
        line = Line(
            start=left,
            end=right)
        return line, left, right, p1['bottom']


def location_code_graph(organization, location_code):
    return graph(
        measurement for measurement in
        models.Measurement.objects.filter(
            location__activity__project__organization=organization,
            location__location_code=location_code,
            location__complete=True).select_related(
            'location',
            'location__activity',
            'location__activity__measurement_type',
            'location__activity__project',
            'location__activity__contractor')
        if (measurement.location.activity.measurement_type.implementation_slug
            == 'dwarsprofiel'))


def graph(measurements):
    data = [PlottingData(m.data, m.location, m.date) for m in measurements]
    from lizard_progress.views import ScreenFigure
    if len(data) == 1:
        fig = ScreenFigure(525, 300)
        ax = fig.add_subplot(111)
        d = data[0]
        ax.set_title(d.title)
        ax.plot(d.distances, d.bottoms, '.-',
                label='Zachte bodem (z2)', linewidth=1.0, color='#663300')
        ax.plot(d.distances, d.tops, '.-',
                label='Harde bodem (z1)', linewidth=1.5, color='k')
        ax.plot([d.baseline.distance_to_midpoint(d.left),
                 d.baseline.distance_to_midpoint(d.right)],
                [d.waterlevel, d.waterlevel],
                label='Waterlijn',
                linewidth=2,
                color='b')
        ax.set_xlim([d.distances[0] - 1, d.distances[-1] + 1])
    else:
        fig = ScreenFigure(1050, 600)
        ax = fig.add_subplot(111)
        colors = get_colors(len(data))
        ax.set_title(
            'Dwarsprofielen van alle projecten op locatie {code}'.format(
                code=data[0].location.location_code))

        for d, color in zip(data, colors):
            ax.plot(
                d.distances, d.bottoms, '.-', linewidth=1.0,
                color=color)
            ax.plot(
                d.distances, d.tops, '.-', linewidth=1.5,
                color=color)
            ax.plot([d.baseline.distance_to_midpoint(d.left),
                     d.baseline.distance_to_midpoint(d.right)],
                    [d.waterlevel, d.waterlevel],
                    label='{project} - {date}'.format(
                        project=d.project,
                        date=d.date),
                    linewidth=2,
                    color=color)
            ax.set_xlim([d.distances[0] - 1, d.distances[-1] + 1])

    ax.set_xlabel('Afstand tot middelpunt watergang (m)')
    ax.set_ylabel('Hoogte (m NAP)')
    ax.legend(bbox_to_anchor=(0.5, 0.9), loc="center")
    ax.grid(True)

    canvas = FigureCanvas(fig)
    return canvas


# Create different colors for the graphs.

# Color code taken from Stack Overflow answer by Janus Troelsen at
# http://stackoverflow.com/questions/470690/how-to-automatically-generate-n-distinct-colors  # NoQA

def zenos_dichotomy():
    """
    http://en.wikipedia.org/wiki/1/2_%2B_1/4_%2B_1/8_%2B_1/16_%2B_%C2%B7_%C2%B7_%C2%B7  # NoQA
    """
    for k in itertools.count():
        yield Fraction(1, 2 ** k)


def getfracs():
    """
    [Fraction(0, 1), Fraction(1, 2), Fraction(1, 4), Fraction(3, 4),
     Fraction(1, 8), Fraction(3, 8), Fraction(5, 8), Fraction(7, 8),
     Fraction(1, 16), Fraction(3, 16), ...]
    [0.0, 0.5, 0.25, 0.75, 0.125, 0.375, 0.625, 0.875, 0.0625, 0.1875, ...]
    """
    yield 0
    for k in zenos_dichotomy():
        i = k.denominator  # [1,2,4,8,16,...]
        for j in range(1, i, 2):
            yield Fraction(j, i)


# can be used for the v in hsv to map linear values 0..1 to something
# that looks equidistant
bias = lambda x: (
    math.sqrt(x / 3) / Fraction(2, 3) + Fraction(1, 3)) / Fraction(6, 5)


def genhsv(h):
    for s in [Fraction(6, 10)]:  # optionally use range
        for v in [Fraction(8, 10)]:  # could use range too
            yield (h, s, v)  # use bias for v here if you use range


genrgb = lambda x: colorsys.hsv_to_rgb(*x)


def genhtml(x):
    uint8tuple = tuple(int(v * 255) for v in x)
    return "#%02x%02x%02x" % uint8tuple


def generate_colors():
    for frac in getfracs():
        for hsv in genhsv(frac):
            yield genhtml(genrgb(hsv))


def get_colors(x):
    """Return list of colors"""
    return list(itertools.islice(generate_colors(), x))
