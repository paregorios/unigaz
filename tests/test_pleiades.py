#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test the unigaz.pleiades module
"""

import logging
from unigaz.pleiades import Pleiades
from pprint import pformat
import pytest

logger = logging.getLogger(__file__)


class TestInit:
    def test_init_no_args(self):
        Pleiades()

    def test_init(self):
        p = Pleiades(user_agent="UnigazTestBot/0.0")
        assert p.web.headers["User-Agent"] == "UnigazTestBot/0.0"
        assert p.web.netloc == "pleiades.stoa.org"


class TestGet:
    def test_get_zucchabar_json(self):
        p = Pleiades(user_agent="UnigazTestBot/0.0")
        uri = "https://pleiades.stoa.org/places/295374/json"
        r = p.get(uri)
        j = r.json()
        assert isinstance(j, dict)
        assert j["title"] == "Zucchabar"
        r = p.get(uri)
        assert r.from_cache
