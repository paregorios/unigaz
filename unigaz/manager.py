#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Manage the tools
"""

import logging
from pprint import pprint
import traceback
from urllib.parse import urlparse
from unigaz.edh import EDH
from unigaz.nominatim import Nominatim
from unigaz.local import Local
from unigaz.pleiades import Pleiades
from unigaz.web import DEFAULT_USER_AGENT, SearchParameterError
import validators

logger = logging.getLogger(__name__)


class Manager:
    def __init__(self, user_agent=DEFAULT_USER_AGENT):
        self.gazetteers = {
            "pleiades": Pleiades(user_agent=user_agent),
            "edh": EDH(user_agent=user_agent),
            "nominatim": Nominatim(user_agent=user_agent),
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

    def local_accession(self, hit):
        if not self.local:
            raise RuntimeError(f"a local gazetteer must be loaded or created first")
        uri = hit["uri"]
        parts = urlparse(uri)
        try:
            g = self.gazetteer_netlocs[parts.netloc]
        except KeyError:
            try:
                g = self.gazetteer_lookup_netlocs[parts.netloc]
            except KeyError:
                raise ValueError(f"Unsupported gazetteer for netloc {parts.netloc}.")
        try:
            source_data, source_uri = g.get_data(uri)
        except Exception as err:
            logger.debug("fail")
            tb = traceback.format_exception(err)
            print("\n".join(tb))
            exit()

        try:
            source_data["title"]
        except KeyError:
            logger.warning(
                f"No title found in data, so using title from search result."
            )
            source_data["title"] = hit["title"]
        else:
            source_data["description"] = hit["title"]

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
            source_data["summary"] = hit["summary"]

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
        return result

    def local_create(self, name):
        if self.local:
            raise NotImplementedError("already got one")
        self.local = Local(title=name)
        return f"Created local gazetteer with title '{self.local.title}'."

    def local_list(self, args):
        if not self.local:
            raise RuntimeError(f"a local gazetteer must be loaded or created first")
        return self.local.content

    def local_merge(self, source, destination):
        if not self.local:
            raise RuntimeError(f"a local gazetteer must be loaded or created first")
        return self.local.merge(source, destination)

    def search(self, gazetteer_name, args):
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
