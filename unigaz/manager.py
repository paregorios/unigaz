#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Manage the tools
"""

import logging
import traceback
from urllib.parse import urlparse
from unigaz.edh import EDH
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
        }
        self.gazetteer_netlocs = dict()
        for k, v in self.gazetteers.items():
            self.gazetteer_netlocs[v.web.netloc] = v
        self.local = None

    def local_accession(self, hit):
        if not self.local:
            raise RuntimeError(f"a local gazetteer must be loaded or created first")
        uri = hit["uri"]
        parts = urlparse(uri)
        g = self.gazetteer_netlocs[parts.netloc]
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
            source_data["title"] = hit["title"]

        v = None
        for k in ["description", "summary", "abstract"]:
            try:
                v = source_data[k]
            except KeyError:
                continue
            else:
                break
        if v is None:
            source_data["summary"] = hit["summary"]

        original = None
        for v in source_data.values():
            if isinstance(v, str):
                if validators.url(v):
                    if v == uri:
                        original = v
                        break
        if original is None:
            try:
                source_data["externals"]
            except KeyError:
                source_data["externals"] = set()
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
