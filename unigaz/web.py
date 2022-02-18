#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Basic web capabilities for gazetteers
"""

from copy import deepcopy
import logging
from textnorm import normalize_space, normalize_unicode
from webiquette.webi import Webi, DEFAULT_HEADERS

DEFAULT_USER_AGENT = "unigaz/0.0.1"
logger = logging.getLogger(__name__)


def norm(s: str):
    return normalize_space(normalize_unicode(s))


class SearchParameterError(RuntimeError):
    def __init__(self, gazetteer: str, message: str = ""):
        self.message = f"Gazetteer '{gazetteer}': {message}"
        super().__init__(self.message)


class Web:
    """Base mixin for providing web-aware functionality to gazetteer classes."""

    def __init__(self, netloc: str, user_agent=DEFAULT_USER_AGENT, **kwargs):
        headers = deepcopy(DEFAULT_HEADERS)
        try:
            ua = norm(user_agent)
        except TypeError:
            pass
        if not ua:
            ua = DEFAULT_USER_AGENT
        if ua == DEFAULT_USER_AGENT:
            logger.warning(
                f'Using default HTTP Request header for User-Agent = "{ua}". '
                "We strongly prefer you define your own unique user-agent string "
                "and pass it to the gazetter object at initialization."
            )
        headers["User-Agent"] = ua
        web_kwargs = dict()
        if kwargs:
            for k, v in kwargs.items():
                if k in {"respect_robots_txt", "cache_control", "expire_after"}:
                    web_kwargs[k] = v

        self.web = Webi(netloc=netloc, headers=headers, **web_kwargs)

    def get(self, uri: str):
        return self.web.get(uri)

    def search(self, **kwargs):
        # override this method to add search functionality
        return None
