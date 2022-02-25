#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Nominatim (OpenStreetMap)
"""

from copy import deepcopy
from datetime import timedelta
from language_tags import tags
import logging
from pprint import pformat, pprint
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

        # copy and reuse all top-level values, except "elements" list
        d = dict()
        for k, v in data.items():
            if k == "elements":
                continue
            d[k] = v

        # verify id and type and add source
        d["source"] = data_uri
        parts = urlparse(data_uri)
        path = parts.path.split("/")
        try:
            path.remove("full")
        except ValueError:
            pass
        id = path[-1]
        osm_type = path[-2]
        try:
            v = d["id"]
        except KeyError:
            pass
        else:
            if str(v) != id:
                raise RuntimeError(f"id mismatch")
        d["id"] = id
        try:
            v = d["type"]
        except KeyError:
            pass
        else:
            if v != osm_type:
                raise RuntimeError(f"osm_type mismatch")
        d["type"] = osm_type

        # parse "elements" list and add values for key themes/topics/attributes

        # title and names
        subtitle, names = self._osm_grok_names(data)
        d["title"] = f"OSM {osm_type} {id}"
        if subtitle:
            d["title"] += f": {subtitle}"
        d["names"] = names

        # locations
        d["locations"] = self._osm_grok_locations(data, d["id"], d["type"])

        # tags2uris etc.

        return d

    def _osm_grok_locations(self, data, id, osm_type):
        # OSM returns elements as a single list; we need them organized by type
        elements_by_type = dict()
        for k in ["node", "way", "relation"]:
            elements = [e for e in data["elements"] if e["type"] == k]
            if len(elements) > 0:
                elements_by_type[f"{k}s"] = elements
        locations = getattr(self, f"_osm_grok_locations_{osm_type}")(
            elements_by_type, parent_id=id
        )
        return locations

    def _osm_grok_locations_node(self, elements_by_type, **kwargs):
        location = dict()
        node = elements_by_type["nodes"][0]
        subtitle = self._osm_grok_title_name([node])
        location["title"] = f"OSM Location "
        if subtitle:
            location["title"] += f"of {subtitle} "
        location["title"] += f"(node {node['id']})"
        lon, lat = self._parse_node_for_lonlat(node)
        location["geometry"] = f"POINT({lon} {lat})"
        return [location]

    def _osm_grok_locations_way(self, elements_by_type, parent_id):
        location = dict()
        subtitle = self._osm_grok_title_name(elements_by_type["ways"])
        location["title"] = f"OSM Location "
        if subtitle:
            location["title"] += f"of {subtitle} "
        waypoint_nodes = dict()
        for node in elements_by_type["nodes"]:
            waypoint_nodes[node["id"]] = node
        waypoints = list()
        the_way = elements_by_type["ways"][0]
        for node_id in the_way["nodes"]:
            waypoints.append(waypoint_nodes[node_id])
        waypoints = [self._parse_node_for_lonlat(wp) for wp in waypoints]
        if waypoints[0][0] == waypoints[-1][0] and waypoints[0][1] == waypoints[-1][1]:
            geo = "POLYGON"
        else:
            geo = "LINESTRING"
        coords = ",".join([f"{wp[0]} {wp[1]}" for wp in waypoints])
        location["geometry"] = f"{geo}({coords})"
        location["title"] += f"(way {parent_id})"
        return [location]

    def _osm_grok_locations_relation(self, elements_by_type, **kwargs):
        locations = list()
        the_relation = elements_by_type["relations"][0]
        for member in the_relation["members"]:
            context = deepcopy(elements_by_type)
            osm_type = member["type"]
            context[osm_type] = [
                e for e in elements_by_type[f"{osm_type}s"] if e["id"] == member["ref"]
            ]
            member_locations = getattr(self, f"_osm_grok_locations_{osm_type}")(
                context, parent_id=member["ref"]
            )
            location = member_locations[0]
            try:
                role = member["role"]
            except KeyError:
                pass
            else:
                title = location["title"]
                if role == "admin_centre":
                    parts = title.split(":")
                    if len(parts) == 2:
                        title = ": ".join(
                            (
                                parts[0],
                                f"Administrative center of {normalize_space(parts[1])}",
                            )
                        )
                    else:
                        title += f" (administrative center)"
                    location["title"] = title
                elif role == "label":
                    parts = title.split(":")
                    if len(parts) == 2:
                        title = ": ".join(
                            (
                                parts[0],
                                f"Central point of {normalize_space(parts[1])}",
                            )
                        )
                    else:
                        title += f" (central point)"
                    location["title"] = title
                elif role == "outer":
                    location["description"] = "outer boundary"
                else:
                    logger.warning(f"Unsupported relation role for location: '{role}'")
            locations.append(location)
        return locations

    def _osm_grok_title_name(self, elements):
        tagged = [e for e in elements if "tags" in e.keys()]
        title_keys = ["name", "name:en"]
        title = None
        for e in tagged:
            for title_key in title_keys:
                try:
                    title = e["tags"][title_key]
                except KeyError:
                    continue
                else:
                    break
        return title

    def _osm_grok_names(self, data):
        elements = [e for e in data["elements"] if "tags" in e.keys()]
        names_by_key = dict()
        for e in elements:
            name_keys = ["name", "name:en"]
            name_keys.extend(
                [
                    k
                    for k in e["tags"].keys()
                    if k.startswith("name") and k not in name_keys
                ]
            )
            name_keys.extend(
                [
                    k
                    for k in e["tags"].keys()
                    if k.startswith("long_name") and k not in name_keys
                ]
            )
            name = None
            for name_key in name_keys:
                try:
                    name = e["tags"][name_key]
                except KeyError:
                    continue
                else:
                    try:
                        names_by_key[name_key]
                    except KeyError:
                        names_by_key[name_key] = set()
                    finally:
                        names_by_key[name_key].add(name)
        names = list()
        title_name = None
        for k, vv in names_by_key.items():
            for v in vv:
                nv = norm(v)
                if k == "name" and title_name is None:
                    title_name = nv
                if k == "name:en" and title_name is None:
                    title_name = nv
                name = {"value": nv}
                keyparts = k.split(":")
                if len(keyparts) == 2:
                    langtag = tags.language(keyparts[1])
                    if langtag:
                        name["language"] = langtag.format
        return (title_name, names)

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
