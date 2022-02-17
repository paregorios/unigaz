#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Define local gazetteer
"""

import logging
from slugify import slugify
import string
from textnorm import normalize_space, normalize_unicode
from uuid import uuid4
from unigaz.gazetteer import Gazetteer

logger = logging.getLogger(__name__)


def norm(s):
    return normalize_space(normalize_unicode(s))


def type_check(what, value, sought_type):
    if not isinstance(value, sought_type):
        raise ValueError(f"Expected {sought_type} for {what}. Got {type(value)}.")


class Index:
    def __init__(self, **kwargs):
        self.raw_index = dict()
        self.cooked_index = dict()
        self.reverse = dict()

    def add(self, key, value):
        try:
            self.raw_index[key]
        except KeyError:
            self.raw_index[key] = set()
        finally:
            self.raw_index[key].add(value)
        cooked_key = self._cook(key)
        try:
            self.cooked_index[cooked_key]
        except KeyError:
            self.cooked_index[cooked_key] = set()
        finally:
            self.cooked_index[cooked_key].add(value)
        try:
            self.reverse[value]
        except KeyError:
            self.reverse[value] = set()
        finally:
            self.reverse[value].add(key)
            self.reverse[value].add(cooked_key)

    def clear(self):
        self.raw_index = dict()
        self.cooked_index = dict()
        self.reverse = dict()

    def delete(self, key):
        for k in [key, self._cook(key)]:
            for idx_name in ["raw_index", "cooked_index"]:
                idx = getattr(self, idx_name)
                try:
                    values = idx[k]
                except KeyError:
                    pass
                else:
                    idx.pop(k)
                    for v in values:
                        self.reverse.pop(v)

    def get_cooked(self, key):
        return self.cooked_index[self._cook(key)]

    def get_raw(self, key):
        return self.raw_index[key]

    def get(self, key):
        try:
            return self.get_raw(key)
        except KeyError:
            try:
                return self.get_cooked(key)
            except KeyError:
                return set()

    def unindex(self, value):
        keys = self.reverse[value]
        for key in keys:
            self.delete(key)

    def _cook(self, value):
        if not isinstance(value, str):
            v = str(value)
        else:
            v = value
        return "-".join(norm(v).lower().split())


class Catalog:
    def __init__(self, indexes: dict = dict()):
        self.indexes = dict()
        for k, v in indexes.items():
            self.indexes[k] = Index(**v)

    def create_index(self, name):
        try:
            self.indexes[name]
        except KeyError:
            self.indexes[name] = Index()

    def index(self, o):
        for idxname, idx in self.indexes.items():
            try:
                entries = getattr(o, idxname)
            except AttributeError:
                logger.error(idxname)
            else:
                if isinstance(entries, str):
                    idx.add(entries, o.id)
                elif isinstance(entries, (list, set)):
                    for entry in entries:
                        if isinstance(entry, str):
                            idx.add(entry, o.id)

    def unindex(self, id):
        for idxname, idx in self.indexes.items():
            idx.unindex(id)


class Identified:
    def __init__(self, **kwargs):
        self._id = uuid4().hex

    @property
    def id(self):
        return self._id


class Titled:
    def __init__(self, **kwargs):
        self._title = None
        try:
            self.title = kwargs["title"]
        except KeyError:
            pass

    @property
    def title(self):
        return self._title

    @title.setter
    def title(self, value: str):
        self._title = norm(value)

    @title.deleter
    def title(self):
        self._title = None

    @property
    def sort_key(self):
        return slugify(self.title, separator="")


class Described:
    def __init__(self, **kwargs):
        self._description = None
        for k in ["description", "summary", "abstract"]:
            try:
                description = kwargs[k]
            except KeyError:
                continue
            try:
                self.description = description
            except ValueError:
                continue
            else:
                break

    @property
    def description(self):
        return self._description

    @description.setter
    def description(self, value):
        v = norm(value)
        if not v:
            raise ValueError(v)
        else:
            self._description = v

    @description.deleter
    def description(self):
        self._description = None


punct_trans = str.maketrans("", "", string.punctuation)


class Indexable:
    def __init__(self, **kwargs):
        try:
            self._catalog = kwargs["catalog"]
        except KeyError:
            self._catalog = None

    def reindex(self):
        if self._catalog:
            self._catalog.unindex(self.id)
            self._catalog.index(self)

    def text_strings(self):
        results = set()
        for attrname, attrval in self.__dict__.items():
            if attrname == "_id":
                continue
            if isinstance(attrval, str):
                results.add(attrval)
            elif isinstance(attrval, (list, set)):
                results.update(attrval)
        return results

    def words(self):
        results = set()
        text_strings = self.text_strings()
        for s in text_strings:
            s = s.translate(punct_trans)
            words = s.split()
            results.update(words)
        return results


class Externals:
    def __init__(self, **kwargs):
        self._externals = dict()


class Dictionary:
    def asdict(self):
        d = dict()
        for varname, varval in vars(self).items():
            if varname.startswith("_"):
                attrname = varname[1:]
                try:
                    attrval = getattr(self, attrname)
                except AttributeError:
                    d[varname] = varval
                else:
                    if varval == attrval:
                        d[attrname] = attrval
                    else:
                        d[varname] = varval
        return d


class Place(Identified, Titled, Described, Externals, Indexable, Dictionary):
    def __init__(self, **kwargs):
        Identified.__init__(self, **kwargs)
        Titled.__init__(self, **kwargs)
        Externals.__init__(self, **kwargs)


class Name(Identified, Externals, Indexable, Dictionary):
    def __init__(self, **kwargs):
        Identified.__init__(self, **kwargs)
        Externals.__init__(self, **kwargs)
        Indexable.__init__(self, **kwargs)
        self._attested_form = None
        self._romanized_forms = list()
        if kwargs:
            for k in [
                "attested_form",
                "attested",
                "romanized_form",
                "romanized_forms",
                "romanized",
            ]:
                try:
                    v = kwargs[k]
                except KeyError:
                    continue
                if k.starts_with("attested"):
                    self.attested_form = v
                elif isinstance(v, str):
                    self.add_romanized_form(v)
                elif isinstance(v, list):
                    self.romanized_forms = v

    @property
    def attested_form(self):
        return self._attested_form

    @attested_form.setter
    def attested_form(self, value: str):
        type_check("attested form", value, str)
        self._attested_form = norm(value)

    @attested_form.deleter
    def attested_form(self):
        self._attested_form = None

    @property
    def romanized_forms(self):
        return self._romanized_forms

    @romanized_forms.setter
    def romanized_forms(self, value: list):
        type_check("romanized forms", value, list)
        self._romanized_forms = [norm(v) for v in value]

    @romanized_forms.deleter
    def romanized_forms(self):
        self._romanized_forms = list()

    def add_romanized_form(self, value: str):
        type_check("romanized form", value, str)
        if value not in self._romanized_forms:
            self._romanized_forms.append(norm(value))

    @property
    def sort_key(self):
        return slugify(self.title, separator="")

    @property
    def title(self):
        if self.attested_form:
            return self.attested_form
        elif self.romanized_forms:
            return self.romanized_forms[0]
        else:
            return ""


class Local(Gazetteer, Titled):
    def __init__(self, **kwargs):
        Titled.__init__(self, **kwargs)
        self._content = dict()
        self._catalog = Catalog()
        for idxname in ["title"]:
            self._catalog.create_index(idxname)
        if not self.title:
            self.title = "Local Gazetteer"

    def add(self, o):
        self._content[o.id] = o
        self._catalog.index(o)

    @property
    def content(self):
        return list(self._content.values())

    def delete(self, id):
        self._content.pop(id)
        self._catalog.unindex()

    def create_from(self, source):
        ftype = None
        if isinstance(source, dict):
            return self._create_from_dict(source)
        elif isinstance(source, str):
            return self._create_from_string(source)
        elif isinstance(source, (list, tuple, set)):
            messages = list()
            for item in source:
                messages.append(self.create_from(item))
            return messages
        else:
            raise NotImplementedError(
                f"create local gazetteer object from {type(source)}"
            )

    def _create_from_dict(self, source):
        try:
            ft = source["feature_type"]
        except KeyError:
            ft = "Place"
        ftl = norm(ft.lower())
        if ftl == "place":
            o = Place(**source)
        elif ftl == "name":
            o = Name(**source)
        else:
            raise ValueError(f"Unrecognized feature type: '{ft}'")
        self.add(o)
        return o

    def _create_from_string(self, source):
        n = Name(attested=source, catalog=self._catalog)
        self.add(n)
        return o

    def get_by_id(self, id):
        return self._content[id]

    def get_by_title(self, title):
        identifiers = self._catalog.indexes["title"].get(title)
        results = [self._content[id] for id in identifiers]
        return results
