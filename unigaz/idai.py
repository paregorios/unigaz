#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
iDAI Gazetteer
https://gazetteer.dainst.org
API docs: https://gazetteer.dainst.org/app/#!/help
"""

from copy import deepcopy
from datetime import timedelta
from language_tags import tags
import logging
from pprint import pformat, pprint
import regex
from slugify import slugify
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


rx_latin_script = regex.compile(r"^\p{IsLatin}+$")


def is_latin_script(s: str):
    if rx_latin_script.match(s):
        return True
    return False


class IDAI(Gazetteer, Web):
    def __init__(self, user_agent=DEFAULT_USER_AGENT):
        Web.__init__(
            self,
            netloc="gazetteer.dainst.org",
            user_agent=user_agent,
            respect_robots_txt=True
            # cache_control=False,
            # expires=timedelta(hours=24),
        )

    def get_data(self, uri):
        parts = urlparse(uri)
        path_parts = parts.path.split("/")
        id_part = str(int(path_parts[1]))
        # https://www.geonames.org/getJSON?id=2491911
        data_uri = urlunparse(
            (
                "https",
                "www.geonames.org",
                f"getJSON",
                "",
                urlencode({"id": id_part}),
                "",
            )
        )
        r = self.get(data_uri)
        if r.status_code != 200:
            r.raise_for_status()
        data = r.json()
        groked = self._geonames_grok(data, data_uri, id_part)
        return (groked, data_uri)

    def _geonames_grok(self, data, data_uri, geoid):
        """Parse and process GeoNames API output for consumption by unigaz"""

        d = dict()
        d["source"] = data_uri
        d["feature_type"] = "Place"
        d["id"] = geoid

        d["names"] = self._geonames_grok_names(
            geoid
        )  # different uri needed for complete name data
        # d["title"] = self._geonames_grok_title(d["names"])  just let search do it
        d["locations"] = self._geonames_grok_locations(data, data_uri)
        d["externals"] = self._geonames_grok_externals(data)
        return d

    def _geonames_grok_externals(self, data):
        externals = set()
        try:
            v = data["wikipediaURL"]
        except KeyError:
            pass
        else:
            if v:
                if validators.url(v):
                    externals.add(v)
        for c in data["alternateNames"]:
            try:
                lang = c["lang"]
            except KeyError:
                continue
            else:
                if lang == "link":
                    v = c["name"]
                    if v:
                        if validators.url(v):
                            externals.add(v)
        return externals

    def _geonames_grok_locations(self, data, source):
        locations = list()
        loc = {
            "geometry": f"POINT({data['lng']} {data['lat']})",
            "title": "GeoNames Coordinates",
            "source": source,
        }
        locations.append(loc)
        return locations

    def _geonames_grok_names(self, geoid):

        names_uri = urlunparse(
            (
                "https",
                "www.geonames.org",
                "/servlet/geonames",
                "",
                urlencode({"geonameId": geoid, "type": "json", "srv": "150"}),
                "",
            )
        )
        r = self.get(names_uri)
        if r.status_code != 200:
            r.raise_for_status()
        data = r.json()

        candidates = [
            n for n in data["geonames"] if n["locale"] not in ["link", "iata", "unlc"]
        ]
        names = list()
        for c in candidates:
            n = dict()
            n["source"] = names_uri
            slug = ""
            if c["name"]:
                n["attested"] = c["name"]
                slug = slugify(c["name"], separator=" ", lowercase=False)
            n["romanized"] = set()
            if c["asciiName"]:
                n["romanized"].add(c["asciiName"])
            if slug:
                n["romanized"].add(slug)
            if c["locale"]:
                lang = tags.language(c["locale"])
                n["language"] = lang.format
                if n["attested"]:
                    if lang.script.format != "Latn":
                        if is_latin_script(n["attested"]):
                            raise RuntimeError(pformat(n, indent=4))
            else:
                n["language"] = "und"
            if c["isOfficialName"]:
                n["official"] = True
            else:
                n["official"] = False
            names.append(n)
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
        """iDAI Gazetteer API Search Interface."""
        these_kwargs = deepcopy(kwargs)
        try:
            these_kwargs["limit"]
        except KeyError:
            these_kwargs["limit"] = "100"
        try:
            v = these_kwargs["text"]
        except KeyError:
            pass
        else:
            these_kwargs["q"] = list(v)
            these_kwargs.pop("text")
        params = self._prep_params(**these_kwargs)
        hits = list()
        uri = urlunparse(
            (
                "https",
                "gazetteer.dainst.org",
                "search.json",
                "",
                params,
                "",
            )
        )
        r = self.get(uri)
        if r.status_code != 200:
            r.raise_for_status()
        data = r.json()
        for entry in data["result"]:
            try:
                title = entry["prefName"]["title"]
            except KeyError:
                title = entry["names"][0]["title"]
            hit = {
                "id": entry["gazId"],
                "feature_type": "Place",
                "uri": entry["@id"],
                "title": title,
                "summary": self._idai_summary(entry),
            }
            hits.append(hit)
        return {"arguments": kwargs, "query": uri, "hits": hits}

    def _idai_summary(self, entry):
        types = "; ".join([t.replace("-", " ") for t in entry["types"]])
        return types.capitalize() + "."
