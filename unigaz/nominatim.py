#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Nominatim (OpenStreetMap)
"""

from copy import deepcopy
from datetime import timedelta
import logging
from textnorm import normalize_space, normalize_unicode
from unigaz.gazetteer import Gazetteer
from unigaz.web import SearchParameterError, Web, DEFAULT_USER_AGENT
from urllib.parse import urlparse, urlencode, urlunparse

logger = logging.getLogger(__name__)


def type_check(what, value, sought_type):
    if not isinstance(value, sought_type):
        raise ValueError(f"Expected {sought_type} for {what}. Got {type(value)}.")


def norm(s: str):
    return normalize_space(normalize_unicode(s))


class Nominatim(Gazetteer, Web):
    def __init__(self, user_agent=DEFAULT_USER_AGENT):
        Web.__init__(
            self,
            netloc="nominatim.openstreetmap.org",
            user_agent=user_agent,
            respect_robots_txt=False,  # nominatim has user-agent * disallow /search, which is nuts, so since they don't respect robots.txt neither will we
            accept="application/json",
            cache_control=False,
            expires=timedelta(hours=24),
        )
        self.lookup_netloc = "www.openstreetmap.org"

    def get_data(self, uri):
        """Get and process OSM data from the OSM API for the given URI"""
        data, data_uri = self._get_data_item(uri)
        groked = self._osm_grok(data, data_uri)

    def _osm_grok(self, data, data_uri):
        """Parse and process OSM API output for consumption by unigaz"""
        d = dict()
        d["source"] = data_uri
        for k, v in data.items():
            if k == "elements":
                continue
            d[k] = v

        # OSM returns elements as a single list; we need them organized by type
        for k in ["node", "way", "relation"]:
            if k in data_uri:
                d["type"] = k
            elements = [e for e in data["elements"] if e["type"] == k]
            if len(elements) > 0:
                d[f"{k}s"] = elements

        d["geometries"] = self._osm_grok_geometry(
            d
        )  # relations can have more than one discrete geom/loc

        return d

    def _osm_grok_geometry(self, data):
        return getattr(self, f"_osm_grok_geometry_{data['type']}")(data)

    def _osm_grok_geometry_node(self, data):
        node = data["nodes"][0]
        data["title"] = self._osm_grok_geometry_title(node)
        data["lon"], data["lat"] = self._parse_node_for_lonlat(node)
        return data

    def _osm_grok_geometry_way(self, data):
        pass

    def _osm_grok_geometry_relation(self, data):
        pass

    def _osm_grok_geometry_title(self, element):
        name_keys = ["name", "name:en"]
        name_keys.extend([k for k in element["tags"].keys() if k.startswith("name")])
        name = None
        for name_key in name_keys:
            try:
                name = element["tags"][name_key]
            except KeyError:
                continue
            else:
                break
        title = f"OSM {element['type']} {element['id']}"
        if name:
            title += f": {name}"
        return title

    def _parse_node_for_lonlat(self, node_data):
        lat = node_data["lat"]
        lon = node_data["lon"]
        return (lon, lat)

    def _parse_waypoints_from_nodelist(self, nodes):
        base_uri = "https://www.openstreetmap.org/node"
        way_points = list()
        for node in nodes:
            node_uri = f"{base_uri}/{node}"
            node_data, node_data_uri = self._get_data_item(node_uri)
            lon, lat = self._parse_node_for_lonlat(node_data)
            way_points.append((lon, lat))
        return way_points

    def _serialize_waypoints_from_nodelist(self, nodes):
        way_points = self._parse_waypoints_from_nodelist(self, nodes)
        return self._serialize_waypoints(way_points)

    def _serialize_waypoints(self, way_points):
        serialized = [f"{wp[0]} {wp[1]}" for wp in way_points]
        serialized = ",".join(serialized)
        if way_points[0] == way_points[-1]:
            wkt = f"POLYGON(({serialized}))"
        else:
            wkt = f"LINESTRING({serialized})"
        return wkt

    def get_datafoo(self, uri):
        data, data_uri = self._get_data_item(uri)
        osm_type = data["type"]
        title = f"OSM {osm_type} {data['id']}"
        try:
            v = data["tags"]["name"]
        except KeyError:
            pass
        else:
            title += f": {v}"
        locations = list()
        if osm_type == "node":
            lon, lat = self._parse_node_for_lonlat(data)
            loc = {
                "title": title,
                "geometry": f"POINT({lon} {lat})",
                "source": data_uri,
            }
            locations.append(loc)
        elif osm_type == "way":
            nodes = [node for node in data["nodes"]]
            loc = {
                "title": title,
                "geometry": self._parse_waypoints_from_nodelist(nodes),
                "source": data_uri,
            }
            locations.append(loc)
        elif osm_type == "relation":
            for role in ["outer", "admin_centre", "label"]:
                title_suffix = role.replace("_", " ")
                members = [m for m in data["members"] if m["role"] == role]
                logger.debug(f"len(members) for role {role}: {len(members)}")
                if (
                    len(members) == 1
                    and members[0]["role"] in ["admin_centre", "label"]
                    and members[0]["type"] == "node"
                ):
                    node_data, node_uri = self._get_data_item(
                        f"https://www.openstreetmap.org/node/{members[0]['ref']}"
                    )
                    lon, lat = self._parse_node_for_lonlat(node_data)
                    loc = {
                        "title": f"{title_suffix} for {title} (node {members[0]['ref']})",
                        "geometry": f"POINT({lon} {lat})",
                        "source": node_uri,
                    }
                    locations.append(loc)
                elif len(members) > 1 and len(
                    [m for m in members if m["type"] == "node"]
                ) == len(members):
                    nodes = [member["ref"] for member in members]
                    loc = {
                        "title": f"{title_suffix} for {title} ({len(members)} nodes in outer ring)",
                        "geometry": self._serialize_waypoints_from_nodelist(nodes),
                        "source": data_uri,
                    }
                    locations.append(loc)
                elif len(members) > 1 and len(
                    [m for m in members if m["type"] == "way"]
                ) == len(members):
                    print("woop")
                    ways = [member["ref"] for member in members]
                    waypoints = list()
                    for member in members:
                        print(f"Member {member['ref']}")
                        way_data, way_uri = self._get_data_item(
                            f"https://www.openstreetmap.org/way/{member['ref']}"
                        )
                        nodes = [node for node in way_data["nodes"]]
                        print(f"Got {len(nodes)} nodes.")
                        waypoints.append(self._parse_waypoints_from_nodelist(nodes))
                    continuous = True
                    print("foo")
                    for i, points in enumerate(waypoints):
                        if i < len(waypoints) - 1:
                            if points[-1] != waypoints[i + 1][-1]:
                                continuous = False
                                break
                        else:
                            if points[-1] != waypoints[0][-1]:
                                continuous = False
                            break
                    print("bar")
                    if continuous:
                        all_waypoints = list()
                        for points in waypoints:
                            all_waypoints.extend(points)
                        loc = {
                            "title": f"{title_suffix} for {title} ({len(members)} ways in outer ring)",
                            "geometry": self._serialize_waypoints(all_waypoints),
                            "source": data_uri,
                        }
                        locations.append(loc)
                    else:
                        for i, points in enumerate(waypoints):
                            loc = {
                                "title": f"{title_suffix} for {title} (way {ways[i]})",
                                "geometry": self._serialize_waypoints(points),
                                "source": f"https://www.openstreetmap.org/way/{members[i]['ref']}",
                            }
                            locations.append(loc)
                else:
                    continue

        else:
            raise NotImplementedError(osm_type)
        data["locations"] = locations
        return (data, data_uri)

    def _get_data_item(self, uri):
        """Get structured OSM data from the OSM API for the given URI"""
        parts = urlparse(uri)
        path = f"/api/0.6{parts.path}"
        if "way" in path or "relation" in path:
            path += "/full"
        json_uri = urlunparse(("https", parts.netloc, path, "", "", ""))
        r = self.get(json_uri)
        if r.status_code != 200:
            r.raise_for_status()
        return (r.json(), json_uri)

    def _massage_params(self, value):
        if isinstance(value, str):
            vals = list()
            vals.append(value)
        else:
            vals = value
        vals = "+".join([norm(v) for v in vals])
        return vals

    def _prep_param_limit(self, value):
        return ("limit", norm(self._massage_params(value)))

    def _prep_param_q(self, value):
        return ("q", norm(self._massage_params(value)))

    def _prep_params(self, **kwargs):
        """Prepare parameters for search URI."""
        params = dict()
        for k, v in kwargs.items():
            try:
                cooked_k, cooked_v = getattr(self, f"_prep_param_{k.lower()}")(v)
            except AttributeError:
                raise SearchParameterError("nominatim", f"Unknown param '{k}':{v}.")
            else:
                params[cooked_k] = cooked_v
        params = self._verify_param_defaults(params)
        params = urlencode(params)
        return params

    def search(self, **kwargs):
        """Nominatim API Search Interface."""
        # https://nominatim.org/release-docs/develop/api/Search/

        param_sets = list()
        these_kwargs = deepcopy(kwargs)
        try:
            these_kwargs["q"]
        except KeyError:
            try:
                v = these_kwargs["text"]
            except KeyError:
                raise NotImplementedError(kwargs)
            else:
                these_kwargs["q"] = v
                these_kwargs.pop("text")
        param_sets.append(self._prep_params(**these_kwargs))
        hits = list()
        queries = list()
        for params in param_sets:
            uri = urlunparse(
                (
                    "https",
                    "nominatim.openstreetmap.org",
                    "/search",
                    "",
                    params,
                    "",
                )
            )
            queries.append(uri)
            logger.debug(f"query uri: {uri}")
            r = self.get(uri)
            if r.status_code != 200:
                r.raise_for_status()
            data = r.json()
            from pprint import pformat

            logger.debug(f"data: {pformat(data, indent=4)}")
            for entry in data:
                hit = {
                    "id": entry["osm_id"],
                    "feature_type": "Place",
                    "uri": f"https://www.openstreetmap.org/{entry['osm_type']}/{entry['osm_id']}",
                    "title": entry["display_name"],
                    "summary": f"{entry['osm_type']}: {entry['category']}: {entry['type']}",
                }
                hits.append(hit)
            hit_ids = set()
            unique_hits = list()
            for hit in hits:
                if hit["id"] in hit_ids:
                    continue
                else:
                    unique_hits.append(hit)
                    hit_ids.add(hit["id"])
        return {"arguments": kwargs, "query": "; ".join(queries), "hits": unique_hits}

    def _verify_param_defaults(self, params):
        defaults = {"limit": "50", "format": "jsonv2"}
        for k, v in defaults.items():
            try:
                params[k]
            except KeyError:
                params[k] = v
        return params
