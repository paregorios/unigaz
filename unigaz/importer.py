#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Importer
"""

import json
from language_tags import tags
import logging
from pathlib import Path
from pprint import pformat
from textnorm import normalize_space, normalize_unicode
from unigaz.writing import classify, codify

logger = logging.getLogger(__name__)


def norm(s: str):
    return normalize_space(normalize_unicode(s))


class ImportError(RuntimeError):
    def __init__(self, msg):
        self.message = msg


class Importer:
    def __init__(self):
        pass

    def import_data(self, filepath):
        """
        Try to import geodata from an arbitrary file
        """
        if isinstance(filepath, Path):
            path = filepath
        elif isinstance(filepath, str):
            path = Path(filepath)
        else:
            raise TypeError(type(filepath))
        filepath = filepath.expanduser().resolve()
        ext = filepath.suffix[1:].lower()
        try:
            return getattr(self, f"_import_{ext}")(filepath)
        except AttributeError:
            raise NotImplementedError(f"Import from {ext} file {str(filepath)}.")

    def _grok_dict(self, input, source):
        result = {"source": source, "feature_type": "Place"}
        for k in ["id", "title", "description", "names", "locations", "references"]:
            part = getattr(self, f"_grok_dict_{k}")(input, source)
            result[k] = part
        return result

    def _grok_dict_field_by_keys(self, input, keys):
        result = None
        for k in keys:
            try:
                result = input[k]
            except KeyError:
                pass
            else:
                if isinstance(result, str):
                    result = norm(result)
                break
        if result is None:
            raise KeyError(f"grok failure (keys: {keys})")
        return result

    def _grok_dict_description(self, input, source):
        try:
            val = self._grok_dict_field_by_keys(
                input, ["description", "summary", "abstract"]
            )
        except KeyError as err:
            msg = f"Import failure for 'description' ({str(err)})"
            raise ValueError(msg)
        attested, romanized, lang, script = classify(val)
        d = {"text": val, "language": codify(lang, script)}
        return d

    def _grok_dict_id(self, input, source):
        try:
            return self._grok_dict_field_by_keys(input, ["id"])
        except KeyError as err:
            msg = f"Import failure for 'id' ({str(err)})"
            raise ValueError(msg)

    def _grok_dict_locations(self, input, source):
        try:
            lon = self._grok_dict_field_by_keys(
                input, ["lon", "long", "lng", "longitude", "x"]
            )
        except KeyError as err:
            msg = f"Import failure for 'location (longitude)' ({str(err)})"
            raise ValueError(msg)
        try:
            lat = self._grok_dict_field_by_keys(input, ["lat", "latitude", "y"])
        except KeyError as err:
            msg = f"Import failure for 'location (latitude)' ({str(err)})"
            raise ValueError(msg)
        loc = {"geometry": f"POINT({lon} {lat})", "title": f"{source} coordinates"}
        return [
            loc,
        ]

    def _grok_dict_names(self, input, source):
        names = list()
        try:
            results = self._grok_dict_field_by_keys(input, ["name"])
        except KeyError as err:
            msg = f"Import failure for 'names' ({str(err)})"
            raise ValueError(msg)
        if isinstance(results, str):
            results = [
                results,
            ]
        else:
            raise NotImplementedError(f"names: {type(results)}")
        for v in results:
            attested, romanized, lang_code, script_code = classify(v)
            name = dict()
            if attested:
                name["attested"] = attested
            name["romanized"] = romanized
            name["language"] = codify(lang_code, script_code)
            names.append(name)
        return names

    def _grok_dict_references(self, input, source):
        return input["references"]

    def _grok_dict_title(self, input, source):
        try:
            return self._grok_dict_field_by_keys(input, ["title", "name"])
        except KeyError as err:
            msg = f"Import failure for 'title' ({str(err)})"
            raise ValueError(msg)

    def _import_json(self, filepath):
        with open(filepath, "r", encoding="utf-8") as fp:
            data = json.load(fp)
        del fp
        source = filepath.basename()
        features = None
        if isinstance(data, dict):
            if len(data) == 1:
                k = list(data.keys())[0]
                if isinstance(data[k], list):
                    features = data[k]
                    source = ": ".join((source, k))
        elif isinstance(data, list):
            features = data
        groked = list()
        for feature in features:
            if isinstance(feature, dict):
                groked.append(self._grok_dict(feature, source))
            else:
                raise NotImplementedError(
                    f"json feature as {feature.__class__.__name__}"
                )
        return groked
