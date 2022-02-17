#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Manage the tools
"""

import logging
from unigaz.local import Local
from unigaz.pleiades import Pleiades
from unigaz.web import DEFAULT_USER_AGENT, SearchParameterError

logger = logging.getLogger(__name__)


class Manager:
    def __init__(self, user_agent=DEFAULT_USER_AGENT):
        self.gazetteers = {"pleiades": Pleiades(user_agent=user_agent)}
        self.gazetteer_netlocs = set()
        for k, v in self.gazetteers.items():
            self.gazetteer_netlocs.add(v.web.netloc)
        self.local = None

    def local_create(self, name):
        if self.local:
            raise NotImplementedError("already got one")
        self.local = Local(title=name)
        return f"Created local gazetteer with title '{self.local.title}'."

    def local_accession(self, args):
        if not self.local:
            raise RuntimeError(f"a local gazetteer must be loaded or created first")
        raise NotImplementedError("local accession")

    def local_list(self, args):
        if not self.local:
            raise RuntimeError(f"a local gazetteer must be loaded or created first")
        content = self.local.content
        content = [(ident, o.title, o.sort_key) for ident, o in content]
        return content

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
                    if g not in self.gazetteer_netlocs:
                        return False
        return True
