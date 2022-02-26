#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Epigraphic Database Heidelberg Geography interface
"""

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


class EDH(Gazetteer, Web):
    def __init__(self, user_agent=DEFAULT_USER_AGENT):
        Web.__init__(
            self,
            netloc="edh.ub.uni-heidelberg.de",
            user_agent=user_agent,
            # cache_control=False,
            # expires=timedelta(hours=24),
        )

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
        groked = self._edh_grok(r.json(), json_uri)
        return (groked, json_uri)

    def _edh_grok(self, data, data_uri):
        """Parse and process EDH API output for consumption by unigaz"""

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

    def _edh_grok_externals(self, data):
        externals = set()
        keys = [k for k in data.keys() if "uri" in k]
        for k in keys:
            v = normalize_space(data[k])
            if validators.url(v):
                externals.add(v)
        return externals

    def _edh_grok_locations(self, data):
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

    def _edh_grok_names(self, data):

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
        if isinstance(value, str):
            vals = list()
            vals.append(value)
        else:
            vals = value
        vals = "+".join([norm(v) for v in vals])
        return vals

    def _prep_param_ancient(self, value):
        return self._prep_param_fo_antik(value)

    # findspot search as documented does not work: it returns limit records with findspot==null
    #    def _prep_param_findspot(self, value):
    #        return ("findspot", norm(self._massage_params(value)))

    def _prep_param_fo_antik(self, value):
        return ("fo_antik", norm(self._massage_params(value)))

    def _prep_param_fo_modern(self, value):
        return ("fo_modern", norm(self._massage_params(value)))

    def _prep_param_limit(self, value):
        return ("limit", norm(self._massage_params(value)))

    def _prep_params(self, **kwargs):
        """Prepare parameters for EDH search."""
        params = dict()
        for k, v in kwargs.items():
            try:
                cooked_k, cooked_v = getattr(self, f"_prep_param_{k.lower()}")(v)
            except AttributeError:
                raise SearchParameterError("edh", f"Unknown param '{k}':{v}.")
            else:
                params[cooked_k] = cooked_v
        params = urlencode(params)
        return params

    def search(self, **kwargs):
        """EDH API Search Interface."""
        param_sets = list()
        these_kwargs = deepcopy(kwargs)
        try:
            these_kwargs["limit"]
        except KeyError:
            these_kwargs["limit"] = "100"
        try:
            v = these_kwargs["text"]
            logger.debug(f"these_kargs[text] = {v}")
        except KeyError:
            try:
                v = these_kwargs["modern"]
            except KeyError:
                param_sets.append(self._prep_params(**these_kwargs))
            else:
                these_kwargs.pop("modern")
                these_kwargs["fo_modern"] = v
                param_sets.append(self._prep_params(**these_kwargs))
                # these_kwargs.pop("fo_modern")
                # these_kwargs["findspot"] = v
                # param_sets.append(self._prep_params(**these_kwargs))
        else:
            these_kwargs.pop("text")
            these_kwargs["fo_modern"] = v
            param_sets.append(self._prep_params(**these_kwargs))
            these_kwargs.pop("fo_modern")
            # these_kwargs["findspot"] = v
            # param_sets.append(self._prep_params(**these_kwargs))
            # these_kwargs.pop("findspot")
            these_kwargs["fo_antik"] = v
            param_sets.append(self._prep_params(**these_kwargs))
        hits = list()
        queries = list()
        for params in param_sets:
            uri = urlunparse(
                (
                    "https",
                    "edh.ub.uni-heidelberg.de",
                    "/data/api/geographie/suche",
                    "",
                    params,
                    "",
                )
            )
            queries.append(uri)
            r = self.get(uri)
            if r.status_code != 200:
                r.raise_for_status()
            data = r.json()
            for entry in data["items"]:
                title = self._edh_title(entry)
                hit = {
                    "id": entry["id"],
                    "feature_type": "Place",
                    "uri": f"https://edh.ub.uni-heidelberg.de/edh/geographie/{entry['id']}",
                    "title": title,
                    "summary": f"{entry['region']}, {entry['country']}",
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

    def _edh_title(self, entry):
        for k in ["findspot", "findspot_modern", "findspot_ancient"]:
            try:
                entry[k]
            except KeyError:
                entry[k] = None
        if entry["findspot_ancient"] and entry["findspot_modern"] and entry["findspot"]:
            title = f"{entry['findspot_ancient']} - {entry['findspot_modern']} ({entry['findspot']})"
        elif entry["findspot_ancient"] and entry["findspot_modern"]:
            title = f"{entry['findspot_ancient']} - {entry['findspot_modern']}"
        elif entry["findspot_ancient"] and entry["findspot"]:
            title = f"{entry['findspot_ancient']} ({entry['findspot']})"
        elif entry["findspot_modern"] and entry["findspot"]:
            title = f"{entry['findspot_modern']} ({entry['findspot']})"
        elif entry["findspot_ancient"]:
            title = f"{entry['findspot_ancient']}"
        elif entry["findspot_modern"]:
            title = f"{entry['findspot_modern']}"
        elif entry["findspot"]:
            title = f"{entry['findspot']}"
        else:
            title = None
        return title
