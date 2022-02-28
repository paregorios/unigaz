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


class TestData:
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

    def test_grok_subtitle(self):
        d = {
            "version": "0.6",
            "generator": "CGImap 0.8.6 (2119652 spike-07.openstreetmap.org)",
            "copyright": "OpenStreetMap and contributors",
            "attribution": "http://www.openstreetmap.org/copyright",
            "license": "http://opendatacommons.org/licenses/odbl/1-0/",
            "elements": [
                {
                    "type": "node",
                    "id": 3028201605,
                    "lat": 36.3047698,
                    "lon": 2.226821,
                    "timestamp": "2020-10-11T21:29:40Z",
                    "version": 19,
                    "changeset": 92314435,
                    "user": "Vejoson",
                    "uid": 11422772,
                    "tags": {
                        "name": "Miliana",
                        "name:ar": "مليانة",
                        "name:ber": "ⵎⴻⵍⵢⴰⵏⴰ",
                        "name:en": "Miliana",
                        "name:es": "Miliana",
                        "name:fr": "Miliana",
                        "name:kab": "Tamelyant",
                        "place": "town",
                        "population": "44201",
                        "postal_code": "44003",
                        "wikidata": "Q48468",
                        "wikipedia": "fr:Miliana",
                    },
                }
            ],
        }
        g = Nominatim(user_agent="UnigazTester/0.0")
        subtitle, names = g._osm_grok_names(d)
        assert subtitle == "Miliana"
        assert len(names) == 5

    def test_grok_node(self):
        g = Nominatim(user_agent="UnigazTester/0.0")
        uri = "https://www.openstreetmap.org/node/3028201605"
        data, data_uri = g._get_data_item(uri)
        groked = g._osm_grok(data, data_uri)
        assert groked["id"] == "3028201605"
        assert groked["type"] == "node"
        assert groked["attribution"] == "http://www.openstreetmap.org/copyright"
        assert groked["title"] == "OSM node 3028201605: Miliana"
        assert len(groked["locations"]) == 1
        assert groked["locations"][0]["geometry"] == "POINT(2.226821 36.3047698)"
        assert len(groked["externals"]) == 2
        externals = sorted(groked["externals"])
        assert externals == [
            "https://fr.wikipedia.org/wiki/Miliana",
            "https://www.wikidata.org/wiki/Q48468",
        ]

    def test_grok_way(self):
        g = Nominatim(user_agent="UnigazTester/0.0")
        uri = "https://www.openstreetmap.org/way/51016872"
        data, data_uri = g._get_data_item(uri)
        groked = g._osm_grok(data, data_uri)
        assert groked["id"] == "51016872"
        assert groked["type"] == "way"
        assert groked["attribution"] == "http://www.openstreetmap.org/copyright"
        assert groked["title"] == "OSM way 51016872: Miliana"
        assert len(groked["locations"]) == 1
        assert groked["locations"][0]["geometry"].startswith("POLYGON")
        assert len(groked["externals"]) == 0

    def test_grok_relation(self):
        g = Nominatim(user_agent="UnigazTester/0.0")
        uri = "https://www.openstreetmap.org/relation/2783389"
        data, data_uri = g._get_data_item(uri)
        groked = g._osm_grok(data, data_uri)
        assert groked["id"] == "2783389"
        assert groked["type"] == "relation"
        assert groked["attribution"] == "http://www.openstreetmap.org/copyright"
        assert groked["title"] == "OSM relation 2783389: Miliana"
        assert len(groked["locations"]) == 4
        geometries = [loc["geometry"] for loc in groked["locations"]]
        for i, geo in enumerate(geometries):
            if i < len(geometries) - 1:
                assert geo != geometries[i + 1]
            else:
                assert geo != geometries[0]

        assert len(groked["externals"]) == 2
        externals = sorted(list(groked["externals"]))
        assert externals == [
            "https://fr.wikipedia.org/wiki/Miliana",
            "https://www.wikidata.org/wiki/Q48468",
        ]


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
