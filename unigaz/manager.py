#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Manage the tools
"""

import logging
from unigaz.pleiades import Pleiades
from unigaz.web import DEFAULT_USER_AGENT

logger = logging.getLogger(__name__)


class Manager:
    def __init__(self, user_agent=DEFAULT_USER_AGENT):
        self.gazetteers = {"pleiades": Pleiades(user_agent=user_agent)}
        self.gazetteer_netlocs = set()
        for k, v in self.gazetteers.items():
            self.gazetteer_netlocs.add(v.web.netloc)

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
