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
    def test_import_dict(self):
        i = Importer()
        fn = "mithraea.json"
        filepath = datapath / fn
        i.import_data(filepath)


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
            "longitude": "41.754227",
            "latitude": "12.285019",
        }
        expected = {
            "id": input["id"],
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
        }
        i = Importer()
        result = i._grok_dict(input, source=source)
        assert result == expected
