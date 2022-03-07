#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test the unigaz.importer module
"""

import logging
from unigaz.importer import Importer
from pathlib import Path
from pprint import pformat
import pytest

logger = logging.getLogger(__file__)
datapath = Path("tests/data")


class TestInit:
    def test_init_no_args(self):
        Importer()


class TestImportJSON:
    def test_import_mithraea(self):
        i = Importer()
        fn = "mithraea.json"
        filepath = datapath / fn
        data = i.import_data(filepath)
        assert isinstance(data, list)
        assert len(data) == 162
        for item in data:
            assert isinstance(item, dict)
        thermae = [
            item for item in data if item["title"] == "Mitreo delle terme di Mitra"
        ]
        assert len(thermae) == 1
        item = thermae[0]
        logger.debug(f">>>{item['source']}<<<")
        assert item["source"].endswith(f"mithraea.json: mithraea")
        assert item["id"] == "1"
        assert len(item["names"]) == 1
        name = item["names"][0]
        sought = {
            "attested": "Mitreo delle terme di Mitra",
            "romanized": {"Mitreo delle terme di Mitra", "mitreo delle terme di mitra"},
            "language": "it",
        }
        assert sought == name
        sought = {
            "text": "The Mithraeum of the terms of Mithras takes its name from being installed in the service area of the Baths of Mithras.",
            "language": "en",
        }
        assert sought == item["description"]
        sought = [
            {
                "bibliographic_uri": "https://www.zotero.org/groups/2533/items/HC8VWRRL",
                "citation_detail": "229",
            }
        ]
        assert sought == item["references"]
        assert len(item["locations"]) == 1
        geometry = item["locations"][0]["geometry"]
        sought = f"POINT(12.285019 41.754227)"
        assert sought == geometry
        assert item["feature_type"] == "Place"
        sought = [{"ctype": "at", "name": "Ostia"}]
        assert item["connects_to"] == sought


class TestGrokDict:
    def test_grok_dict(self):
        source = "foo"
        input = {
            "id": "1",
            "uri": "https://www.mithraeum.eu/monument/1",
            "name": "Mitreo delle terme di Mitra",
            "description": "The Mithraeum of the terms of Mithras takes its name from being installed in the service area of the Baths of Mithras.",
            "types": ["mithraeum", "place", "sanctuary"],
            "references": [
                {
                    "bibliographic_uri": "https://www.zotero.org/groups/2533/items/HC8VWRRL",
                    "citation_detail": "229",
                }
            ],
            "connects_to": [{"ctype": "at", "name": "Ostia"}],
            "latitude": "41.754227",
            "longitude": "12.285019",
        }
        expected = {
            "id": input["id"],
            "uri": input["uri"],
            "source": source,
            "title": input["name"],
            # "description": input["description"],
            "description": {"text": input["description"], "language": "en"},
            "feature_type": "Place",
            "names": [
                {
                    "attested": input["name"],
                    "romanized": {input["name"], input["name"].lower()},
                    "language": "it",
                }
            ],
            "locations": [
                {
                    "geometry": f"POINT({input['longitude']} {input['latitude']})",
                    "title": f"{source} coordinates",
                }
            ],
            "references": input["references"],
            "connects_to": [{"ctype": "at", "name": "Ostia"}],
        }
        i = Importer()
        result = i._grok_dict(input, source=source)
        assert result == expected
