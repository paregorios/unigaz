#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Define local gazetteer
"""

from copy import deepcopy
import datetime
import json
import logging
from math import asin, atan2, cos, degrees, sin, pi, radians
from os import sep
from pathlib import Path
import re
from shapely import wkt
from shapely.geometry import Point, LineString, Polygon, mapping, shape
from shapely.ops import unary_union
from slugify import slugify
import string
from textnorm import normalize_space, normalize_unicode
import traceback
from uuid import uuid4
from unigaz.gazetteer import Gazetteer
from urllib.parse import urlparse
import validators

logger = logging.getLogger(__name__)
rx_camel2snake = re.compile(r"(?<!^)(?=[A-Z])")
rx_shapely_wkt = re.compile(r"^(POINT|LINESTRING|POLYGON)\s*\(.+\)$")
rx_dd_latlon = re.compile(
    r"^(?P<latitude>(-|\+)?\d+\.\d+)\s*,?\s*(?P<longitude>(-|\+)?\d+\.\d+)$"
)
rx_dd_lonlat = re.compile(
    r"^(?P<longitude>(-|\+)?\d+\.\d+)\s*,?\s*(?P<latitude>(-|\+)?\d+\.\d+)$"
)


def camel2snake(s):
    return rx_camel2snake.sub("_", s).lower()


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
        self._descriptions = list()
        self._preferred_description = None
        for k in ["description", "summary", "abstract"]:
            try:
                description = kwargs[k]
            except KeyError:
                continue
            else:
                try:
                    source = kwargs["source"]
                except KeyError:
                    source = None
                if isinstance(description, str):
                    self.add_description(text=description, source=source)
                elif isinstance(description, dict):
                    try:
                        v = description["source"]
                    except KeyError:
                        description["source"] = source
                    else:
                        if v is None:
                            description["source"] = source
                    self.add_description(**description)

    @property
    def descriptions(self):
        return self._descriptions

    @descriptions.deleter
    def descriptions(self):
        self._descriptions = list()

    def add_description(self, text=None, lang="und", preferred=False, source=None):
        d = {"text": text, "lang": lang, "preferred": preferred, "source": source}
        if preferred:
            self._preferred_description = d
        self._descriptions.append(d)

    @property
    def preferred_description(self):
        return self._preferred_description


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
        try:
            source = kwargs["source"]
        except KeyError:
            source = None
        for k in ["external", "uri"]:
            try:
                v = kwargs[k]
            except KeyError:
                continue
            if not validators.url(v):
                continue
            self.add_external(v, source)
        try:
            values = kwargs["externals"]
        except KeyError:
            pass
        else:
            if isinstance(values, str):
                self.add_external(values, source)
            elif isinstance(values, (list, set, tuple)):
                for v in values:
                    self.add_external(v, source)
        for v in kwargs.values():
            logger.debug(f"foo: {v}")
            if isinstance(v, str):
                if validators.url(v):
                    self.add_external(v, source)

    @property
    def externals(self):
        return self._externals

    @externals.deleter
    def externals(self):
        self._externals = dict()

    @externals.setter
    def externals(self, values):
        del self.externals
        for v in values:
            self.add_external(*v)

    def add_external(self, uri, source=None):
        if validators.url(uri):
            try:
                self._externals[uri]
            except KeyError:
                self._externals[uri] = set()
        else:
            raise ValueError(f"invalid URI: {uri}")
        if isinstance(source, str):
            self._externals[uri].add(source)
        elif isinstance(source, (set, list, tuple)):
            self._externals[uri].update(source)
        else:
            raise TypeError(f"source: {type(source)}")


class Dictionary:
    def asdict(self):
        d = dict()
        for varname, varval in vars(self).items():
            if varname in ["_catalog", "_preferred_description"]:
                continue
            if varname.startswith("_"):
                attrname = varname[1:]
            else:
                attrname = varname
            try:
                attrval = getattr(self, attrname)
            except AttributeError:
                attrval = None
            if varval == attrval:
                val = attrval
            else:
                val = varval
            d[attrname] = self._asdict_process(val)
        return d

    def _asdict_process(self, value):

        if isinstance(value, (list, set, tuple)):
            return [self._asdict_process(v) for v in value]
        elif isinstance(value, dict):
            return {k: self._asdict_process(v) for k, v in value.items()}
        elif isinstance(value, Dictionary):
            return value.asdict()
        elif isinstance(value, (Point, LineString, Polygon)):
            return mapping(value)
        else:
            return value
        return d


class DictionaryEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Dictionary):
            return obj.asdict()
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)


class Journaled:
    def __init__(self, **kwargs):
        self._journal = dict()
        self.add_journal_event("created", None)
        try:
            v = kwargs["journal_event"]
        except KeyError:
            pass
        else:
            if v:
                self.add_journal_event(*v)

    @property
    def journal_events(self):
        return self._journal

    def add_journal_event(self, verb, source, datetime_stamp=None):
        if datetime_stamp:
            dtstamp = datetime_stamp
        else:
            dtstamp = (
                datetime.datetime.utcnow()
                .replace(tzinfo=datetime.timezone.utc)
                .isoformat()
            )
        try:
            self._journal[dtstamp]
        except KeyError:
            self._journal[dtstamp] = {verb: source}
        else:
            self._journal[dtstamp][verb] = source

    @property
    def journal(self):
        return self._journal

    @property
    def created(self):
        for dtstamp, journal_entries in self._journal.items():
            try:
                source = journal_entries["created"]
            except KeyError:
                continue
            return (dtstamp, source)

    @property
    def sources(self):
        source_list = list()
        for dtstamp, journal_entries in self._journal.items():
            for verb in ["created_from", "merged_from"]:
                try:
                    source = journal_entries[verb]
                except KeyError:
                    continue
                source_list.append(source)
        return source_list


class Place(Identified, Titled, Described, Externals, Indexable, Dictionary, Journaled):
    def __init__(self, **kwargs):
        Identified.__init__(self, **kwargs)
        Titled.__init__(self, **kwargs)
        Described.__init__(self, **kwargs)
        Externals.__init__(self, **kwargs)
        Indexable.__init__(self, **kwargs)
        Journaled.__init__(self, **kwargs)
        self._locations = list()
        self._locations_grok(**kwargs)
        self._names = list()
        self._names_grok(**kwargs)

    def add_location(self, value):
        if isinstance(value, Location):
            self._locations.append(value)
        else:
            raise NotImplementedError(f"add_location: {type(value)}.")

    def add_name(self, value):
        if isinstance(value, Name):
            self._names.append(value)
        else:
            raise NotImplementedError(f"add_name: {type(value)}")

    def _footprint(self, accuracy_buffer=True):
        collection = [l.geometry for l in self.locations]
        if accuracy_buffer:
            collection.extend([l.accuracy_bubble for l in self.locations])
        collection = [g for g in collection if g is not None]
        from pprint import pformat

        logger.debug(f"collection in footprint: {pformat(collection, indent=4)}")
        return unary_union(collection)

    def convex_hull(self, accuracy_buffer=True):
        footprint = self._footprint(accuracy_buffer=accuracy_buffer)
        return footprint.convex_hull

    def envelope(self, accuracy_buffer=True):
        footprint = self._footprint(accuracy_buffer=accuracy_buffer)
        return footprint.envelope

    def mapping(self, format="geojson"):
        """Return a geojson representation of self."""
        if format == "geojson":
            d = {
                "type": "FeatureCollection",
                "features": [l.mapping() for l in self.locations],
            }
        else:
            raise NotImplementedError(f"mapping format={format}")
        return d

    def merge(self, source):
        """Merge data from source object into self."""
        if isinstance(source, Place):
            return self._merge_place(source)
        elif isinstance(source, Name):
            return self.add_name(source)
        elif isinstance(source, Location):
            return self.add_location(source)
        else:
            raise TypeError(type(source))

    @property
    def locations(self):
        return self._locations

    def minimum_rotated_rectangle(self, accuracy_buffer=True):
        if accuracy_buffer:
            footprint = self._footprint_accuracy()
        else:
            footprint = self._footprint()
        return footprint.minimum_rotated_rectangle

    @property
    def names(self):
        return self._names

    def representative_point(self):
        footprint = self._footprint()
        return footprint.representative_point()

    def _merge_place(self, source):
        """Merge data from Place(source) into self."""
        s_created, s_origin = source.created
        if source.title != self.title:
            self.add_description(text=source.title, source=s_origin)
        for sd in source.descriptions:
            d = deepcopy(sd)
            if sd["source"] is None:
                d["source"] = s_origin
            self.add_description(**d)
        for uri, e_source in source.externals.items():
            if e_source is None:
                e_source = s_origin
            self.add_external(uri, e_source)
        for name in source.names:
            self.add_name(name)
        for location in source.locations:
            self.add_location(location)
        for dt_stamp, events in source.journal_events.items():
            for verb, whence in events.items():
                if verb != "created":
                    self.add_journal_event(verb, whence, dt_stamp)
        self.add_journal_event("merged_from", source.title)
        return self

    def _locations_grok(self, **kwargs):
        try:
            source = kwargs["source"]
        except KeyError:
            source = None
        locations = list()
        if source is None:
            return self.add_location(**kwargs)
        else:
            parts = urlparse(source)
            try:
                grokker = getattr(
                    self,
                    f"_locations_grok_{parts.netloc.replace('.', '_').replace('-', '_')}",
                )
            except KeyError:
                pass
            else:
                these_locations = grokker(**kwargs)
                for l in these_locations:
                    l.source = source
                locations.extend(these_locations)
        for l in these_locations:
            self.add_location(l)

    def _locations_grok_edh_ub_uni_heidelberg_de(self, **kwargs):
        # EDH locations
        keys = [k for k in kwargs.keys() if k.startswith("coordinates")]
        locations = list()
        for k in keys:
            coords = kwargs[k]
            lat, lon = [float(norm(c)) for c in coords.split(",")]
            n = Location(
                geometry=f"POINT({lon} {lat})",
                title="EDH Coordinates",
            )
            n.add_journal_event("created from", kwargs["source"])
            locations.append(n)
        return locations

    def _locations_grok_pleiades_stoa_org(self, **kwargs):
        # Pleiades locations
        locations = list()
        for pl in kwargs["locations"]:
            n = Location(source=kwargs["source"], **pl)
            n.add_journal_event("created from", kwargs["source"])
            locations.append(n)
        return locations

    def _names_grok(self, **kwargs):
        try:
            source = kwargs["source"]
        except KeyError:
            source = None
        names = list()
        if source is None:
            return self.add_name(**kwargs)
        else:
            parts = urlparse(source)
            try:
                grokker = getattr(
                    self,
                    f"_names_grok_{parts.netloc.replace('.', '_').replace('-', '_')}",
                )
            except KeyError:
                pass
            else:
                these_names = grokker(**kwargs)
                for n in these_names:
                    n.source = source
                names.extend(these_names)
        for n in names:
            self.add_name(n)

    def _names_grok_edh_ub_uni_heidelberg_de(self, **kwargs):
        # EDH names
        names = list()
        for k in ["findspot", "findspot_modern"]:
            try:
                v = kwargs[k]
            except KeyError:
                pass
            else:
                if v:
                    n = Name()
                    n.attested_form = v
                    n.add_romanized_form(v)
                    if k == "findspot_modern":
                        n.language = "de"
                n.add_journal_event("created_from", kwargs["source"])
                names.append(n)
        try:
            v = kwargs["findspot_ancient"]
        except KeyError:
            pass
        else:
            n = Name()
            n.add_romanized_form(v)
            n.add_journal_event("created from", kwargs["source"])
            names.append(n)
        return names

    def _names_grok_pleiades_stoa_org(self, **kwargs):
        # Pleiades names
        names = list()
        for pn in kwargs["names"]:
            n = Name(source=kwargs["source"], **pn)
            n.add_journal_event("created from", kwargs["source"])
            names.append(n)
        return names


class Location(
    Identified, Titled, Described, Externals, Indexable, Dictionary, Journaled
):
    def __init__(self, **kwargs):
        Identified.__init__(self, **kwargs)
        Titled.__init__(self, **kwargs)
        Described.__init__(self, **kwargs)
        Externals.__init__(self, **kwargs)
        Indexable.__init__(self, **kwargs)
        Journaled.__init__(self, **kwargs)
        self._geometry = None
        try:
            self.geometry = kwargs["geometry"]
        except KeyError:
            pass
        try:
            self.accuracy_radius = kwargs["accuracy_value"]
        except KeyError:
            self.accuracy_radius = None

    def mapping(self, format="geojson"):
        "Return a dict serializable to the specified format"
        try:
            return getattr(self, f"_mapping_{format}")()
        except AttributeError:
            raise NotImplementedError(f"mapping format={format}")

    def _mapping_geojson(self):
        d = {
            "type": "Feature",
            "geometry": mapping(self.geometry),
            "properties": {
                "title": self.title,
                "accuracy_radius": self.accuracy_radius,
            },
        }
        return d

    @property
    def accuracy_bubble(self):
        if self.accuracy_radius is None:
            return None
        origin = self.geometry.representative_point()
        origin_lon = radians(origin.x)
        origin_lat = radians(origin.y)
        distance = self.accuracy_radius  # meters
        earth_radius = 6378137.0  # WGS84 mean radius
        angular_distance = distance / earth_radius
        termini = list()
        bearing = 0.0
        while True:
            if bearing >= 2.0 * pi:
                break
            dest_lat = asin(
                sin(origin_lat) * cos(angular_distance)
                + cos(origin_lat) * sin(angular_distance) * cos(bearing)
            )
            dest_lon = origin_lon + atan2(
                sin(bearing) * sin(angular_distance) * cos(origin_lat),
                cos(angular_distance) - sin(origin_lat) * sin(dest_lat),
            )
            termini.append(Point(degrees(dest_lon), degrees(dest_lat)))
            bearing += pi / 8.0
        for t in termini:
            logger.debug(f"terminus: {t.wkt}")
        if isinstance(self.geometry, Point):
            bubble = unary_union(termini).convex_hull
        else:
            d_dd = max([t.hausdorff_distance(origin) for t in termini])
            bubble = self.geometry.convex_hull.buffer(d_dd)
        logger.debug(f"bubble: {bubble.wkt}")
        return bubble

    @property
    def geometry(self):
        return self._geometry

    @geometry.setter
    def geometry(self, geometry):
        if isinstance(geometry, (Point, LineString, Polygon)):
            self._geometry = geometry
        elif isinstance(geometry, dict):
            self._geometry = shape(geometry)
        elif isinstance(geometry, str):
            if rx_shapely_wkt.match(geometry):
                self._geometry = wkt.loads(geometry)
            else:
                raise ValueError(geometry)
        else:
            raise ValueError(geometry)

    @geometry.deleter
    def geometry(self):
        self._geometry = None


class Name(Identified, Externals, Indexable, Dictionary, Journaled):
    def __init__(self, **kwargs):
        Identified.__init__(self, **kwargs)
        Externals.__init__(self, **kwargs)
        Indexable.__init__(self, **kwargs)
        Journaled.__init__(self, **kwargs)

        self._attested_form = None
        self._romanized_forms = list()
        self._language = "und"
        self.source = None
        self.name_type = None
        self.transcription_accuracy = None
        self.association_certainty = None
        self.transcription_completeness = None
        if kwargs:
            source = kwargs["source"]
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
                if k.startswith("attested"):
                    self.attested_form = v
                elif isinstance(v, str):
                    self.add_romanized_form(v)
                elif isinstance(v, list):
                    self.romanized_forms = v
            for k in [
                "language",
                "nameType",
                "transcriptionAccuracy",
                "associationCertainty",
                "transcriptionCompleteness",
            ]:
                try:
                    v = kwargs[k]
                except KeyError:
                    continue
                else:
                    v = norm(v)
                    if v:
                        k_snake = camel2snake(k)
                        setattr(self, k_snake, norm(v))

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
    def language(self):
        return self._language

    @language.setter
    def language(self, value: str):
        # TBD: validate language code
        self._language = norm(value)

    @language.deleter
    def language(self):
        self._language = "und"

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

    def create_from(self, source_data, source):
        if isinstance(source_data, dict):
            return self._create_from_dict(source_data, source)
        elif isinstance(source_data, str):
            return self._create_from_string(source_data, source)
        elif isinstance(source_data, (list, tuple, set)):
            messages = list()
            for item in source_data:
                messages.append(self.create_from(item, source))
            return messages
        else:
            raise NotImplementedError(
                f"create local gazetteer object from {type(source_data)}"
            )

    def _create_from_dict(self, source_data, source):
        logger.debug("_create_from_dict")
        journal_event = None
        if source:
            journal_event = ("created from", source)
        try:
            ft = source_data["feature_type"]
        except KeyError:
            ft = "Place"
        ftl = norm(ft.lower())
        logger.debug(ftl)
        if ftl == "place":
            try:
                o = Place(**source_data, journal_event=journal_event, source=source)
            except Exception as err:
                tb = traceback.format_exception(err)
                print("\n".join(tb))
                exit()
        elif ftl == "name":
            o = Name(**source_data, journal_event=journal_event)
        else:
            raise ValueError(f"Unrecognized feature type: '{ft}'")
        logger.debug("adding ...")
        self.add(o)
        logger.debug("... added")
        return o

    def _create_from_string(self, source_data, source):
        logger.debug("_create_from_dict")
        journal_event = None
        if source:
            journal_event = ("created from", source)
        n = Name(
            attested=source_data, catalog=self._catalog, journal_event=journal_event
        )
        self.add(n)
        return n

    def export(self, format="json"):
        """
        Export contents of the local gazetteer.
        """
        try:
            func = getattr(self, f"_export_{format}")
        except AttributeError:
            raise NotImplementedError(f"unsupported export format {format}")
        return func()

    def _export_json(self):
        filepath = self._export_filepath()
        filepath = filepath.with_suffix(".json")
        data = {"title": self.title, "content": self.content}
        with open(filepath, "w", encoding="utf-8") as fp:
            json.dump(data, fp, ensure_ascii=False, indent=4, cls=DictionaryEncoder)
        del fp
        return f"Wrote {len(self.content)} entries in local gazetteer to JSON file {filepath.resolve()}."

    def _export_filepath(self):
        dirpath = Path("data/exports")
        dirpath.mkdir(parents=True, exist_ok=True)
        dtstamp = (
            "".join(
                (
                    datetime.datetime.utcnow()
                    .replace(tzinfo=datetime.timezone.utc)
                    .isoformat()
                ).split(":")[0:2]
            )
            .replace("T", "")
            .replace("-", "")
        )
        fn = "_".join((slugify(f"{self.title}", separator="_"), dtstamp))
        filepath = dirpath / fn
        return filepath

    def get_by_id(self, id):
        return self._content[id]

    def get_by_title(self, title):
        identifiers = self._catalog.indexes["title"].get(title)
        results = [self._content[id] for id in identifiers]
        return results

    def merge(self, source, destination):
        return destination.merge(source)
