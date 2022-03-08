#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Manage the tools
"""

from copy import deepcopy
import jsonpickle
import logging
from pathlib import Path
from pprint import pprint, pformat
from slugify import slugify
import traceback
from urllib.parse import urlparse
from unigaz.edh import EDH
from unigaz.geo import axes, bubble
from unigaz.geonames import GeoNames
from unigaz.idai import IDAI
from unigaz.importer import Importer
from unigaz.nominatim import Nominatim
from unigaz.local import Local
from unigaz.pleiades import Pleiades
from unigaz.web import DEFAULT_USER_AGENT, SearchParameterError
import validators

logger = logging.getLogger(__name__)


class Manager:
    def __init__(self, user_agent=DEFAULT_USER_AGENT):
        self.gazetteers = {
            "edh": EDH(user_agent=user_agent),
            "geonames": GeoNames(user_agent=user_agent),
            "idai": IDAI(user_agent=user_agent),
            "nominatim": Nominatim(user_agent=user_agent),
            "pleiades": Pleiades(user_agent=user_agent),
        }
        self.gazetteer_netlocs = dict()
        self.gazetteer_lookup_netlocs = dict()
        for k, g in self.gazetteers.items():
            self.gazetteer_netlocs[g.web.netloc] = g
            try:
                lu = g.lookup_netloc
            except AttributeError:
                pass
            else:
                self.gazetteer_lookup_netlocs[lu] = g
        self.local = None

    def import_from_file(self, filepath):
        """Import features from a file."""
        if isinstance(filepath, str):
            fp = Path(filepath)
        else:
            fp = filepath
        try:
            self.file_importer
        except AttributeError:
            self.file_importer = Importer()
        data = self.file_importer.import_data(fp)
        return data

    def local_accession(self, hit, fetch_data=True):
        """Accession an item from search or other external context into the local gazetteer."""
        if not self.local:
            raise RuntimeError(f"a local gazetteer must be loaded or created first")
        uri = hit["uri"]
        if fetch_data:
            parts = urlparse(uri)
            try:
                g = self.gazetteer_netlocs[parts.netloc]
            except KeyError:
                try:
                    g = self.gazetteer_lookup_netlocs[parts.netloc]
                except KeyError:
                    raise ValueError(
                        f"Unsupported gazetteer for netloc {parts.netloc}."
                    )
            try:
                source_data, source_uri = g.get_data(uri)
            except Exception as err:
                logger.debug("fail")
                tb = traceback.format_exception(err)
                print("\n".join(tb))
                exit()
        else:
            source_data = hit
            source_uri = hit["uri"]

        additional_description = None
        try:
            source_title = source_data["title"]
        except KeyError:
            logger.warning(
                f"No title found in data, so using title from search result."
            )
            source_data["title"] = hit["title"]
        else:
            if source_title != hit["title"]:
                additional_description = hit["title"]

        v = None
        for k in ["description", "summary", "abstract"]:
            try:
                v = source_data[k]
            except KeyError:
                continue
            else:
                break
        if v is None:
            logger.warning(
                f"No summary/description found in data, so using content from search result."
            )
            try:
                source_data["summary"] = hit["summary"]
            except KeyError:
                pass

        try:
            source_data["externals"]
        except KeyError:
            source_data["externals"] = set()
            for v in source_data.values():
                if isinstance(v, str):
                    if validators.url(v):
                        source_data["externals"].add(v)
        source_data["externals"].add(uri)

        try:
            result = self.local.create_from(source_data, source_uri)
        except Exception as err:
            tb = traceback.format_exception(err)
            return "\n".join(tb)
        if additional_description:
            result.add_description(additional_description, source=uri)
        return result

    def local_align(self, gazetteer_name, tolerance=5000.0, limit=1):
        """Align to designated gazetteer."""
        if self.supported(gazetteer_name):
            for p in self.local.content:
                g = self.gazetteers[gazetteer_name]
                strings = set()
                for n in p.names:
                    if n.attested_form:
                        strings.add(n.attested_form)
                    for r in list(n.romanized_forms):
                        strings.add(r)
                if len(strings) == 0:
                    strings.add(p.title)
                kwargs = {"text": strings}
                if p.locations:
                    bounds = bubble(p.convex_hull(), tolerance).bounds
                    bounds = [f"{b:.5f}" for b in bounds]
                    logger.debug(f"bounds: {pformat(bounds, indent=4)}")
                    kwargs["lowerLeft"] = ",".join(bounds[0:2])
                    kwargs["upperRight"] = ",".join(bounds[2:4])
                    kwargs["predicate"] = "intersection"
                    kwargs["locationPrecision:list"] = "precise"
                logger.debug(pformat(kwargs, indent=4))
                try:
                    results = g.search(**kwargs)
                except SearchParameterError as err:
                    raise ValueError(f"search parameter error: {str(err)}")
                else:
                    if len(results["hits"]) == limit:
                        print("VICTORY!")
                        pprint(results["hits"], indent=4)
                    elif len(results["hits"]) == 0:
                        print("MISS!")
                    else:
                        print(f"YOU HAVE BEEN DEFEATED (HITS={len(results['hits'])})")

        else:
            raise ValueError(f"gazetteer '{gazetteer_name}' is not supported.")

    def local_change(self, feature, fieldname, sequence, *args):
        """Modify a local field on a feature."""
        if isinstance(sequence, str):
            i = int(sequence)
        elif isinstance(sequence, int):
            i = sequence
        else:
            raise TypeError(f"For sequence expected str or int. Got {type(sequence)}.")
        i = i - 1
        fn = fieldname
        try:
            field = getattr(feature, fn)
        except AttributeError:
            fn = f"{fieldname}s"
            try:
                field = getattr(feature, f"{fn}")
            except AttributeError:
                raise
        if isinstance(field, list):
            field_item = field[i]
            if len(args) != 2:
                raise ValueError(f"len(args)={len(args)}. Expected 2.")
            if isinstance(field_item, dict):
                if args[1].lower() == "false":
                    new_value = False
                elif args[1].lower() == "true":
                    new_value = True
                else:
                    new_value = args[1]
                old_value = field_item[args[0]]
                field_item[args[0]] = new_value
            else:
                raise NotImplementedError(
                    f"field_item {fn}[{i}] type={type(field_item)}"
                )
        else:
            raise NotImplementedError(f"field {fn} type={type(field)}")
        return f"Changed {fn} {sequence} on {feature.title} from {args[0]}={old_value} to {args[0]}={new_value}."

    def local_create(self, name):
        """Create a local gazetteer."""
        if self.local:
            raise NotImplementedError("already got one")
        self.local = Local(title=name)
        return f"Created local gazetteer with title '{self.local.title}'."

    def local_duplicate(self, feature, fieldname, sequence, *args):
        """Duplicate a local field on feature."""
        if isinstance(sequence, str):
            i = int(sequence)
        elif isinstance(sequence, int):
            i = sequence
        else:
            raise TypeError(f"For sequence expected str or int. Got {type(sequence)}.")
        i = i - 1
        try:
            source = getattr(feature, fieldname)
        except AttributeError:
            try:
                source = getattr(feature, f"{fieldname}s")
            except AttributeError:
                raise
        if isinstance(source, list):
            new = deepcopy(source[i])
            if isinstance(new, dict):
                getattr(feature, f"add_{fieldname}")(**new)
            else:
                raise NotImplementedError(f"new type={type(new)}")
        else:
            raise NotImplementedError(
                f"duplicate source {fieldname} of type {type(source)}"
            )
        return f"Duplicated {fieldname} {sequence} on {feature.title}."

    def local_list(self, args):
        """List the contents of the local gazetteer."""
        if not self.local:
            raise RuntimeError(f"a local gazetteer must be loaded or created first")
        return self.local.content

    def local_load(self, local_name):
        """Load a previously saved local gazetteer."""
        if self.local:
            raise RuntimeError(f"a local gazetteer is already loaded")
        path = Path("data/gazetteers")
        fn = slugify(local_name, separator="_")
        path = path / f"{fn}.json"
        path = path.resolve()
        with open(path, "r", encoding="utf-8") as fp:
            pickled = fp.read()
        del fp
        self.local = jsonpickle.decode(pickled)
        return f"Loaded local gazetteer {self.local.title} from {path}."

    def local_merge(self, source, destination):
        """Merge two items in a local gazetteer."""
        if not self.local:
            raise RuntimeError(f"a local gazetteer must be loaded or created first")
        return self.local.merge(source, destination)

    def local_save(self):
        """Save the local gazetteer."""
        if not self.local:
            raise RuntimeError(f"a local gazetteer must be loaded or created first")
        path = Path("data/gazetteers")
        path.mkdir(parents=True, exist_ok=True)
        fn = slugify(self.local.title, separator="_")
        path = path / f"{fn}.json"
        path = path.resolve()
        pickled = jsonpickle.encode(self.local)
        with open(path, "w", encoding="utf-8") as fp:
            fp.write(pickled)
        del fp
        return f"Saved local gazetteer {self.local.title} to {path}."

    def search(self, gazetteer_name, args):
        """Search for features in supported external gazetteer sources."""
        if self.supported(gazetteer_name):
            g = self.gazetteers[gazetteer_name]
            kwargs = {"text": set()}
            for arg in args:
                parts = arg.split(":")
                if len(parts) == 1:
                    kwargs["text"].add(parts[0])
                elif len(parts) == 2:
                    kwargs[parts[0]] = parts[1]
                else:
                    raise ValueError(f"unrecognized argument {arg}")
            if len(kwargs["text"]) == 0:
                kwargs.pop("text")
            try:
                results = g.search(**kwargs)
            except SearchParameterError as err:
                raise ValueError(f"search parameter error: {str(err)}")
        else:
            raise ValueError(f"gazetteer '{gazetteer_name}' is not supported.")
        return results

    def supported(self, args):
        """What gazetteers are supported?"""
        if not args:
            supported = list()
            for k, v in self.gazetteers.items():
                supported.append((k, v.web.netloc))
            return supported
        else:
            if isinstance(args, str):
                these_args = [
                    args,
                ]
            else:
                these_args = args
            for arg in these_args:
                g = arg.lower()
                try:
                    self.gazetteers[g]
                except KeyError:
                    try:
                        self.gazetteer_netlocs[g]
                    except KeyError:
                        return False
        return True
