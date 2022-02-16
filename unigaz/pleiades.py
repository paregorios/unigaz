#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pleiades Gazetteer interface
"""

from copy import deepcopy
from datetime import timedelta
import feedparser
import logging
from textnorm import normalize_space, normalize_unicode
from unigaz.gazetteer import Gazetteer
from unigaz.web import SearchParameterError, Web, DEFAULT_USER_AGENT
from urllib.parse import urlencode, urlunparse

logger = logging.getLogger(__name__)


def type_check(what, value, sought_type):
    if not isinstance(value, sought_type):
        raise ValueError(f"Expected {sought_type} for {what}. Got {type(value)}.")


def norm(s: str):
    return normalize_space(normalize_unicode(s))


class Pleiades(Gazetteer, Web):
    def __init__(self, user_agent=DEFAULT_USER_AGENT):
        # ignore cache control response headers from Pleiades because right now "expires" is always from 2012
        Web.__init__(
            self,
            netloc="pleiades.stoa.org",
            user_agent=user_agent,
            cache_control=False,
            expires=timedelta(hours=24),
        )

    def search(self, **kwargs):
        return self._search_rss(**kwargs)

    def _prep_param_title(self, value):
        type_check("Title parameter", value, str)
        return ("Title", norm(value))

    def _prep_params(self, **kwargs):
        """Prepare parameters for Pleiades search."""
        params = dict()
        for k, v in kwargs.items():
            try:
                cooked_k, cooked_v = getattr(self, f"_prep_param_{k.lower()}")(v)
            except AttributeError:
                raise SearchParameterError("pleiades", f"Unknown param '{k}':{v}.")
            else:
                params[cooked_k] = cooked_v
        params = self._verify_param_defaults(params)
        params = urlencode(params)
        return params

    def _search_rss(self, **kwargs):
        """Use Pleiades RSS search interface since it gives us back structured data."""
        params = self._prep_params(**kwargs)
        uri = urlunparse(("https", "pleiades.stoa.org", "/search_rss", "", params, ""))
        r = self.get(uri)
        hits = list()
        data = feedparser.parse(r.text)
        for entry in data.entries:
            hits.append(
                {
                    "id": entry.link.split("/")[-1],
                    "feature_type": entry.dc_type,
                    "uri": entry.link,
                    "title": entry.title,
                    "summary": entry.description,
                }
            )
        return {"arguments": kwargs, "query": uri, "hits": hits}

    def _verify_param_defaults(self, params):
        defaults = {"review_state": "published", "portal_type": "Place"}
        for k, v in defaults.items():
            try:
                params[k]
            except KeyError:
                params[k] = v
        return params
