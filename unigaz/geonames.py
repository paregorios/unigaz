#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GeoNames
"""

from bs4 import BeautifulSoup
from copy import deepcopy
from datetime import timedelta
import logging
from textnorm import normalize_space, normalize_unicode
from unigaz.gazetteer import Gazetteer
from unigaz.web import SearchParameterError, Web, DEFAULT_USER_AGENT
from urllib.parse import urlparse, urlencode, urlunparse
import validators

logger = logging.getLogger(__name__)


def type_check(what, value, sought_type):
    if not isinstance(value, sought_type):
        raise ValueError(f"Expected {sought_type} for {what}. Got {type(value)}.")


def norm(s: str):
    return normalize_space(normalize_unicode(s))


class GeoNames(Gazetteer, Web):
    def __init__(self, user_agent=DEFAULT_USER_AGENT):
        Web.__init__(
            self,
            netloc="secure.geonames.org",
            user_agent=user_agent,
            respect_robots_txt=False,  # geonames has user-agent * disallow /search, which is nuts, so since they don't respect robots.txt neither will we
            # cache_control=False,
            # expires=timedelta(hours=24),
        )
        self.lookup_netloc = "www.geonames.org"

    def get_data(self, uri):
        parts = urlparse(uri)
        path_parts = parts.path.split("/")
        json_part = [p for p in path_parts if p == "json"]
        if not json_part:
            if path_parts[-1] == "":
                path_parts[-1] = "json"
            else:
                path_parts.append("json")
        json_uri = urlunparse(("https", parts.netloc, "/".join(path_parts), "", "", ""))
        r = self.get(json_uri)
        if r.status_code != 200:
            r.raise_for_status()
        groked = self._geonames_grok(r.json(), json_uri)
        return (groked, json_uri)

    def _geonames_grok(self, data, data_uri):
        """Parse and process GeoNames API output for consumption by unigaz"""

        d = dict()
        item = data["items"]

        d["source"] = data_uri
        d["feature_type"] = "Place"
        d["id"] = item["id"]
        d["title"] = self._edh_title(item)
        d["names"] = self._edh_grok_names(item)
        d["locations"] = self._edh_grok_locations(item)
        d["externals"] = self._edh_grok_externals(item)

        return d

    def _geonames_grok_externals(self, data):
        externals = set()
        keys = [k for k in data.keys() if "uri" in k]
        for k in keys:
            v = normalize_space(data[k])
            if validators.url(v):
                externals.add(v)
        return externals

    def _geonames_grok_locations(self, data):
        keys = [k for k in data.keys() if k.startswith("coordinates")]
        locations = list()
        for k in keys:
            coords = data[k]
            lat, lon = [float(norm(c)) for c in coords.split(",")]
            loc = {
                "geometry": f"POINT({lon} {lat})",
                "title": "EDH Coordinates",
                "source": f"https://edh.ub.uni-heidelberg.de/edh/geographie/{data['id']}/json",
            }
            locations.append(loc)
        return locations

    def _geonames_grok_names(self, data):

        names = list()
        source = f"https://edh.ub.uni-heidelberg.de/edh/geographie/{data['id']}/json"
        for k in ["findspot", "findspot_modern"]:
            try:
                v = data[k]
            except KeyError:
                pass
            else:
                if v:
                    nv = norm(v)
                    name = {"language": "und", "romanized": list(), "source": source}
                    name["attested"] = nv
                    name["romanized"].append(nv)
                    if k == "findspot_modern":
                        name["language"] = "de"
                    name["name_type"] = "geographic"
                    names.append(name)
        try:
            v = data["findspot_ancient"]
        except KeyError:
            pass
        else:
            if v:
                nv = norm(v)
                name = {"language": "und", "romanized": list(), "source": source}
                name["romanized"].append(nv)
                name["name_type"] = "geographic"
                names.append(name)
        return names

    def _massage_params(self, value):
        if isinstance(value, bool):
            vals = list()
            vals.append(str(value))
        elif isinstance(value, str):
            vals = list()
            vals.append(value)
        else:
            vals = value
        vals = "+".join([norm(v) for v in vals])
        return vals

    def _prep_param_isnamerequired(self, value):
        return ("isNameRequired", norm(self._massage_params(value)))

    def _prep_param_limit(self, value):
        return ("limit", norm(self._massage_params(value)))

    def _prep_param_maxrows(self, value):
        return ("maxRows", norm(self._massage_params(value)))

    def _prep_param_name(self, value):
        return ("name", norm(self._massage_params(value)))

    def _prep_param_q(self, value):
        return ("q", norm(self._massage_params(value)))

    def _prep_param_username(self, value):
        return ("username", norm(self._massage_params(value)))

    def _prep_params(self, **kwargs):
        """Prepare parameters for EDH search."""
        params = dict()
        for k, v in kwargs.items():
            try:
                cooked_k, cooked_v = getattr(self, f"_prep_param_{k.lower()}")(v)
            except AttributeError:
                raise SearchParameterError("geonames", f"Unknown param '{k}':{v}.")
            else:
                params[cooked_k] = cooked_v
        params = urlencode(params)
        return params

    def search(self, **kwargs):
        """GeoNames API Search Interface."""
        these_kwargs = deepcopy(kwargs)
        try:
            these_kwargs["username"]
        except KeyError:
            raise ValueError(f"GeoNames search requires a username argument.")
        try:
            limit = these_kwargs["limit"]
        except KeyError:
            pass
        else:
            these_kwargs["maxRows"] = limit
            these_kwargs.pop("limit")
        try:
            these_kwargs["maxRows"]
        except KeyError:
            these_kwargs["maxRows"] = "100"
        try:
            v = these_kwargs["text"]
        except KeyError:
            pass
        else:
            these_kwargs["q"] = list(v)
            these_kwargs.pop("text")
            these_kwargs["isNameRequired"] = False
        try:
            v = these_kwargs["name"]
        except KeyError:
            pass
        else:
            these_kwargs["name"] = list(v)
            these_kwargs["isNameRequired"] = True
        params = self._prep_params(**these_kwargs)
        hits = list()
        uri = urlunparse(
            (
                "https",
                "secure.geonames.org",
                "searchJSON",
                "",
                params,
                "",
            )
        )
        r = self.get(uri)
        if r.status_code != 200:
            r.raise_for_status()
        data = r.json()
        for entry in data["geonames"]:
            try:
                title = entry["toponymName"]
            except KeyError:
                title = entry["name"]
            hit = {
                "id": entry["geonameId"],
                "feature_type": "Place",
                "uri": f"https://www.geonames.org/{entry['geonameId']}",
                "title": entry["toponymName"],
                "summary": self._geonames_summary(entry),
            }
            hits.append(hit)
        return {"arguments": kwargs, "query": uri, "hits": hits}

    def _geonames_summary(self, entry):
        summary = [
            f"{entry['fcodeName'].capitalize()}.",
            f"{entry['adminName1'].capitalize()}, {entry['countryName']}.",
        ]
        return " ".join(summary)
