#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
iDAI Gazetteer
https://gazetteer.dainst.org
API docs: https://gazetteer.dainst.org/app/#!/help
"""

from copy import deepcopy
from datetime import timedelta
from iso639 import Lang as Lang639
from language_tags import tags
import logging
import pinyin
from pprint import pformat, pprint
import regex
from shapely.geometry import shape, Polygon
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
            respect_robots_txt=True,
            cache_control=False,
            expires=timedelta(hours=24),
        )

    def get_data(self, uri):
        parts = urlparse(uri)
        path_parts = parts.path.split("/")
        path_parts = [p for p in path_parts if p.strip()]
        id_part = str(int(path_parts[-1]))
        # https://gazetteer.dainst.org/doc/12345
        data_uri = urlunparse(
            (
                "https",
                "gazetteer.dainst.org",
                f"doc/{id_part}.json",
                "",
                "",
                "",
            )
        )
        r = self.get(data_uri)
        if r.status_code != 200:
            r.raise_for_status()
        data = r.json()
        groked = self._idai_grok(data, data_uri, id_part)
        return (groked, data_uri)

    def _idai_grok(self, data, data_uri, geoid):
        """Parse and process iDAI gazetteer API output for consumption by unigaz"""

        d = dict()
        d["source"] = data_uri
        d["feature_type"] = "Place"
        d["id"] = geoid

        d["names"] = self._idai_grok_names(data, data_uri)
        d["title"] = self._idai_grok_title(data, data_uri)
        d["locations"] = self._idai_grok_locations(data, data_uri)
        d["externals"] = self._idai_grok_externals(data, data_uri)
        return d

    def _idai_grok_externals(self, data, data_uri):
        externals = set()
        bypassed = set()
        for ident in data["identifiers"]:
            c = ident["context"]
            v = ident["value"]
            if c in ["zenon-systemnr"]:
                continue
            elif c == "zenon-thesaurus":
                externals.add(
                    urlunparse(
                        (
                            "https",
                            "zenon.dainst.org",
                            "Search/Results",
                            "",
                            urlencode({"lookfor": self._massage_params(v)}),
                            "",
                        )
                    )
                )
            elif c == "geonames":
                externals.add(f"https://www.geonames.org/{v}")
            elif c == "pleiades":
                externals.add(f"https://pleiades.stoa.org/places/{v}")
            else:
                bypassed.add(c)
        for link in data["links"]:
            if link["predicate"] == "owl:sameAs":
                parts = urlparse(link["object"])
                if parts.netloc == "sws.geonames.org":
                    externals.add(
                        urlunparse(
                            ("https", "www.geonames.org", parts.path, "", "", "")
                        )
                    )
                elif parts.netloc == "d-nb.info":
                    externals.add(link["object"])
                else:
                    bypassed.add(parts.netloc)
        if bypassed:
            logger.warning(
                f"Bypassed when parsing iDAI externals: {' '.join(list(bypassed))}"
            )
        return externals

    def _idai_grok_locations(self, data, source):
        locations = list()
        try:
            geo = data["prefLocation"]
        except KeyError:
            return locations
        try:
            coords = geo["coordinates"]
        except KeyError:
            pass
        else:
            loc = {
                "title": "iDAI Point Location",
                "geometry": f"POINT({coords[0]} {coords[1]})",
                "source": source,
            }
            locations.append(loc)
        try:
            ishape = geo["shape"]
        except KeyError:
            pass
        else:
            s = Polygon(ishape[0][0])
            loc = {
                "title": f"iDAI Polygon Location",
                "geometry": s.wkt,
                "source": source,
            }
            locations.append(loc)
        return locations

    def _idai_grok_names(self, data, source):

        candidates = [n for n in data["names"]]
        try:
            v = data["prefName"]
        except KeyError:
            pass
        else:
            candidates.append(v)
        names = list()
        for c in candidates:
            n = dict()
            n["source"] = source
            slug = ""
            try:
                ancient = c["ancient"]
            except KeyError:
                ancient = False
            try:
                language = c["language"]
            except KeyError:
                language = "und"
            else:
                try:
                    language = tags.language(Lang639(language).pt1).format
                except AttributeError:
                    raise RuntimeError(f"bad language code: {language}")
            val = c["title"]
            latn = is_latin_script(val)
            n["romanized"] = set()
            if latn:
                n["romanized"].add(val)
            if latn and ancient and language in ["la", "und"]:
                n["language"] = "la"
                n["attested"] = val
            elif latn and not ancient and language != "und":
                n["language"] = language
                if tags.language(language).script.format == "Latn":
                    n["attested"] = val
            elif not latn:
                n["language"] = language
                n["attested"] = val
            slug = slugify(val, separator=" ", lowercase=False)
            if slug:
                n["romanized"].add(slug)
            if language in ["cmn", "zh"] and not latn:
                n["romanized"].add(pinyin.get(val))
                n["romanized"].add(pinyin.get(val, format="strip", delimiter=" "))
                n["romanized"].add(pinyin.get(val, format="numerical"))
            names.append(n)
        return names

    def _idai_grok_title(self, data, source):
        try:
            v = data["prefName"]
        except KeyError:
            return None
        else:
            return v["title"]

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
        try:
            types = "; ".join([t.replace("-", " ") for t in entry["types"]])
        except KeyError:
            return None
        return types.capitalize() + "."
