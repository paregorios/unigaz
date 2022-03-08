#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
geographic utilities
"""

import logging
from math import asin, atan2, cos, degrees, pi, radians, sin
from os import minor
from shapely.geometry import LineString, Point
from shapely.ops import unary_union

logger = logging.getLogger(__name__)


def bubble(origin_shape, buffer_distance):
    origin = origin_shape.centroid
    origin_lon = radians(origin.x)
    origin_lat = radians(origin.y)
    distance = origin_shape.length + buffer_distance
    earth_radius = 6378137.0  # WGS84 mean radius
    angular_distance = distance / earth_radius
    termini = list()
    bearing = 0.0
    while True:
        if bearing >= 2.0 * pi:
            break
        dest_lat = asin(
            sin(origin_lat) * cos(angular_distance)
            + cos(origin_lat) * sin(angular_distance) * cos(bearing)
        )
        dest_lon = origin_lon + atan2(
            sin(bearing) * sin(angular_distance) * cos(origin_lat),
            cos(angular_distance) - sin(origin_lat) * sin(dest_lat),
        )
        termini.append(Point(degrees(dest_lon), degrees(dest_lat)))
        bearing += pi / 19.0
    for t in termini:
        logger.debug(f"terminus: {t.wkt}")
    if isinstance(origin_shape, Point):
        bub = unary_union(termini).convex_hull
    else:
        d_dd = max([t.hausdorff_distance(origin_shape) for t in termini])
        bub = origin_shape.convex_hull.buffer(d_dd)
    return bub


def axes(origin_shape):
    mbr_points = list(zip(*origin_shape.minimum_rotated_rectangle.exterior.coords.xy))
    mbr_lengths = [
        LineString((mbr_points[i], mbr_points[i + 1])).length
        for i in range(len(mbr_points) - 1)
    ]
    minor_axis = round(min(mbr_lengths), 2)
    major_axis = round(max(mbr_lengths), 2)
    return (major_axis, minor_axis)
