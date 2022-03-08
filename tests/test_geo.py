#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test the unigaz.geo module
"""

import logging
from math import pi, sqrt
from shapely.geometry import LineString, Point, Polygon
from unigaz.geo import bubble

logger = logging.getLogger(__file__)


class TestBubble:
    def test_point_zero_zero(self):
        s = Point(0.0, 0.0)
        b = bubble(s, 111319.491)
        assert isinstance(b, Polygon)
        area = b.area
        radius = sqrt(area / pi)
        assert round(radius, 2) == 1.0

    def test_point_69_38(self):
        s = Point(69.0, 38.0)
        b = bubble(s, 55500.607)
        assert isinstance(b, Polygon)
        mbr_points = list(zip(*b.minimum_rotated_rectangle.exterior.coords.xy))
        mbr_lengths = [
            LineString((mbr_points[i], mbr_points[i + 1])).length
            for i in range(len(mbr_points) - 1)
        ]
        minor_axis = round(min(mbr_lengths), 2)
        major_axis = round(max(mbr_lengths), 2)
        assert minor_axis == 1.0
        assert major_axis == 1.26

    def test_point_m6_59(self):
        s = Point(-6.0, 59.0)
        b = bubble(s, 55293.722)
        assert isinstance(b, Polygon)
        mbr_points = list(zip(*b.minimum_rotated_rectangle.exterior.coords.xy))
        mbr_lengths = [
            LineString((mbr_points[i], mbr_points[i + 1])).length
            for i in range(len(mbr_points) - 1)
        ]
        minor_axis = round(min(mbr_lengths), 2)
        major_axis = round(max(mbr_lengths), 2)
        assert minor_axis == 0.99
        assert major_axis == 1.92

    def test_poly_zero_zero(self):
        s = Polygon(((0, 0), (0, 1), (1, 1), (1, 0), (0, 0)))
        b = bubble(s, 111319.491)
        area = b.area
        radius = sqrt(area / pi)
        assert round(radius, 2) == 2.32
