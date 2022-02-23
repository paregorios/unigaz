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
            respect_robots_txt=False  # nominatim has user-agent * disallow /search, which is nuts, so since they don't respect robots.txt neither will we
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
        return (r.json()["items"], json_uri)

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
