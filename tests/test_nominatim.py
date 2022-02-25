#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test the unigaz.nominatim module
"""

import logging
from unigaz.nominatim import Nominatim
from pprint import pformat
import pytest

logger = logging.getLogger(__file__)


class TestInit:
    def test_init_no_args(self):
        Nominatim()

    def test_init(self):
        p = Nominatim(user_agent="UnigazTester/0.0")
        assert p.web.headers["User-Agent"] == "UnigazTester/0.0"
        assert p.web.netloc == "nominatim.openstreetmap.org"


class TestGetDataItem:
    def test_get_node_json(self):
        g = Nominatim(user_agent="UnigazTester/0.0")
        uri = "https://www.openstreetmap.org/node/3028201605"
        j, juri = g._get_data_item(uri)
        assert isinstance(j, dict)
        assert len(j["elements"]) == 1
        assert j["elements"][0]["type"] == "node"

    def test_get_way_json(self):
        g = Nominatim(user_agent="UnigazTester/0.0")
        uri = "https://www.openstreetmap.org/way/51016872"
        j, juri = g._get_data_item(uri)
        assert isinstance(j, dict)
        assert len(j["elements"]) > 1
        assert len([e for e in j["elements"] if e["type"] == "node"]) > 1
        assert len([e for e in j["elements"] if e["type"] == "way"]) == 1

    def test_get_relation_json(self):
        g = Nominatim(user_agent="UnigazTester/0.0")
        uri = "https://www.openstreetmap.org/relation/2783389"
        j, juri = g._get_data_item(uri)
        assert isinstance(j, dict)
        assert len(j["elements"]) > 1
        assert len([e for e in j["elements"] if e["type"] == "node"]) > 1
        assert len([e for e in j["elements"] if e["type"] == "way"]) > 1
        assert len([e for e in j["elements"] if e["type"] == "relation"]) == 1


# class TestSearch:
#     def test_search_title(self):
#         p = Nominatim(user_agent="UnigazTester/0.0")
#         results = p.search(title="Miliana")
#         assert isinstance(results, dict)
#         assert results["arguments"] == {"title": "Miliana"}
#         assert (
#             results["query"]
#             == "https://pleiades.stoa.org/search_rss?Title=Zucchabar&review_state=published&portal_type=Place"
#         )
#         assert len(results["hits"]) == 3
#         assert results["hits"][0]["title"] == "Zucchabar"
#         r = p.get(results["hits"][0]["uri"])
#         assert "Zucchabar" in r.text
