#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interpreter to provide a clean API for interacting with ocmnponents
"""

from enum import auto
import folium
import json
from inspect import getdoc
import logging
from pprint import pformat
from rich.table import Table
from rich.pretty import Pretty
from shapely.geometry import mapping, Point, LineString, Polygon
import shlex
from tempfile import mkstemp, TemporaryDirectory
from unigaz.local import Place
from unigaz.manager import Manager
from unigaz.web import SearchParameterError
import webbrowser


logger = logging.getLogger(__name__)


class UsageError(Exception):
    def __init__(self, command: str, message: str = "", usage: str = None):
        self.message = f"On command '{command}': {message}"
        if usage:
            self.message += f"\nUsage:\n{usage}."
        super().__init__(self.message)


class ArgumentError(Exception):
    def __init__(self, command: str, message: str = ""):
        self.message = f"On command '{command}': {message}"
        super().__init__(self.message)


class CommandError(RuntimeError):
    def __init__(self, command: str, message: str):
        self.message = f"During command '{command}': {message}"
        super().__init__(self.message)


class Interpreter:
    def __init__(self):
        self._temp_dir = TemporaryDirectory()
        self.commands = [
            "_".join(a.split("_")[2:]) for a in dir(self) if a.startswith("_cmd_")
        ]
        aliases = {
            "?": "help",
            "g": "gazetteer",
            "q": "quit",
            "level": "log_level",
            "debug": "log_debug",
            "warning": "log_warning",
            "info": "log_info",
            "error": "log_error",
        }
        for a, cmd in aliases.items():
            try:
                getattr(self, f"_cmd_{cmd}")
            except AttributeError:
                pass
            else:
                try:
                    self.aliases
                except AttributeError:
                    self.aliases = dict()
                finally:
                    self.aliases[a] = cmd
        self.reverse_aliases = {}
        for a, v in self.aliases.items():
            try:
                self.reverse_aliases[v]
            except KeyError:
                self.reverse_aliases[v] = list()
            finally:
                self.reverse_aliases[v].append(a)
        for v, aliases in self.reverse_aliases.items():
            aliases.sort()

        self.manager = Manager(user_agent="UniGazInteractive/0.1")

        self.external_context = dict()
        self.local_context = dict()

    def parse(self, raw_input):
        parts = shlex.split(raw_input)
        cmd = parts[0]
        if cmd not in self.commands:
            try:
                cmd = self.aliases[cmd]
            except KeyError:
                return f"Unrecognized command '{cmd}'"
        r = getattr(self, f"_cmd_{cmd}")(parts[1:])
        return r

    def _cmd_accession(self, args):
        """
        Accession an item from search results into local
            > accession search 1
        """
        expected = ["search"]
        if len(args) != 2 or args[0] not in expected:
            expected = [f"'{e}'" for e in expected]
            raise ArgumentError(
                "accession", f"expected {' or '.join(expected)}, got {' '.join(args)}"
            )
        i = args[1]
        if args[0] == "search":
            try:
                hit = self.external_context[i]
            except KeyError:
                raise ArgumentError(f"Number {i} not in external search context.")
        result = self.manager.local_accession(hit)
        return f"Created {result.__class__.__name__} '{result.title}' from external source.'"

    def _cmd_create(self, args):
        """
        Create a local gazetteer.
            > create My Sites
        """
        results = self.manager.local_create(" ".join(args))
        return results

    def _cmd_export(self, args):
        """
        Export places in local gazetteer to standard file formats
            > export json
        """
        if len(args) != 1:
            raise UsageError(
                "export", f"expected 1 argument (format), got {len(args)}: {args}"
            )
        return self.manager.local.export(format=args[0])

    def _cmd_gazetteer(self, args):
        """
        Check for gazetteer support.
            > gazetteer pleiades
              responds with True or False
            > gazetteer
              responds with list (like 'gazetteers' command)
        """
        r = self.manager.supported(args)
        if isinstance(r, bool):
            return r
        elif isinstance(r, list):
            return self._table(("short name", "netloc"), r)

    def _cmd_gazetteers(self, args):
        """
        List supported gazetteers.
            > gazetteers
        """
        gazetteers = self.manager.supported(args)
        return self._table(("short name", "netloc"), gazetteers)

    def _cmd_help(self, args):
        """
        Get help with available commands.
            > help (lists all available commands)
            > help {command} (prints usage for the indicated command)
        """
        if args:
            cmd = args
            try:
                msg = getdoc(getattr(self, f"_cmd_{cmd}"))
            except AttributeError:
                raise ArgumentError(
                    "help",
                    'Unrecognized command {cmd}. Try "help" to get a list of commands.',
                )
            else:
                try:
                    aliases = self.reverse_aliases[cmd]
                except KeyError:
                    pass
                else:
                    aliases = ", ".join(aliases)
                    msg += f"\nAliases: {aliases}"
            return msg
        else:
            entries = [
                (k, getdoc(getattr(self, f"_cmd_{k}")).splitlines()[0])
                for k in self.commands
            ]
            entries.sort(key=lambda x: x[0])
            return self._table(columns=("command", "documentation"), rows=entries)

    def _cmd_list(self, args):
        """
        List contents of collections
            > list local
            > list search
        """
        expected = ["local", "search"]
        if len(args) > 1 or len(args) == 0 or args[0] not in expected:
            expected = [f"'{e}'" for e in expected]
            raise ArgumentError("list", f"expected {' or '.join(expected)}, got {args}")
        if args[0] == "local":
            if not self.manager.local:
                raise CommandError(
                    "list", "a local gazetteer must be created or loaded first"
                )
            content_list = self.manager.local_list(args)
            self.local_context = dict()
            context = self.local_context
            content_title = self.manager.local.title
        elif args[0] == "search":
            raise NotImplementedError("list search")
        content_list.sort(key=lambda o: o.sort_key)
        rows = list()
        for i, o in enumerate(content_list):
            if o.preferred_description:
                row = (
                    f"{i+1}",
                    f"{o.__class__.__name__}: {o.title}\n{o.preferred_description['text']}",
                )
            elif o.descriptions:
                dlist = "\n".join([d["text"] for d in o.descriptions])
                row = (
                    f"{i+1}",
                    f"{o.__class__.__name__}: {o.title}\n{dlist}",
                )
            rows.append(row)
            context[str(i + 1)] = o
        return self._table(
            title=f"{content_title}: {len(content_list)} items",
            columns=[f"{args[0]} context", "summary"],
            rows=rows,
        )

    def _cmd_log_debug(self, args):
        """
        Change logging level to DEBUG
        """
        logging.getLogger().setLevel(level=logging.DEBUG)
        return self._cmd_log_level(args)

    def _cmd_log_error(self, args):
        """
        Change logging level to ERROR
        """
        logging.getLogger().setLevel(level=logging.ERROR)
        return self._cmd_log_level(args)

    def _cmd_log_info(self, args):
        """
        Change logging level to INFO
        """
        logging.getLogger().setLevel(level=logging.INFO)
        return self._cmd_log_level(args)

    def _cmd_log_level(self, args):
        """
        Get the current logging level.
        """
        levels = {
            logging.DEBUG: "DEBUG",
            logging.INFO: "INFO",
            logging.WARNING: "WARNING",
            logging.ERROR: "ERROR",
        }
        val = levels[logging.root.level]
        return val

    def _cmd_log_warning(self, args):
        """
        Change logging level to WARNING
        """
        logging.getLogger().setLevel(level=logging.WARNING)
        return self._cmd_log_level(args)

    def _cmd_map(self, args):
        """
        Display a map of the indicated Place
            > map local 2
        """
        o = self._context_lookup(args, "map")
        logger.debug(f"type(o): {type(o)}")
        m = folium.Map(height="72%", width="100%")

        if isinstance(o, Place):
            for location in o.locations:
                geometry = location.geometry
                if isinstance(geometry, Point):
                    folium.Marker(
                        location=(geometry.y, geometry.x),
                        popup=location.title,
                        icon=folium.Icon(color="orange"),
                    ).add_to(m)
                elif isinstance(geometry, LineString):
                    print(f"Polyline! {pformat(list(geometry.coords), indent=1)}")
                    folium.PolyLine(
                        locations=[(pair[1], pair[0]) for pair in geometry.coords],
                        popup=location.title,
                        color="orange",
                    ).add_to(m)
                elif isinstance(geometry, Polygon):
                    folium.Polygon(
                        locations=[(pair[1], pair[0]) for pair in geometry.coords],
                        popup=location.title,
                        color="orange",
                        fill_color="orange",
                        fill=True,
                        fill_opacity=0.5,
                    ).add_to(m)

        boundp = o.convex_hull()
        if isinstance(boundp, Polygon):
            folium.Polygon(
                locations=[(pair[1], pair[0]) for pair in boundp.exterior.coords],
                popup="horizontal accuracy bubble",
                color="blue",
                opacity=0.6,
                dash_array="10 10",
            ).add_to(m)
        bbox = o.envelope().bounds
        bbox = [[bbox[1], bbox[0]], [bbox[3], bbox[2]]]
        m.fit_bounds(bbox)
        fd, filepath = mkstemp(suffix=".html", dir=self._temp_dir.name, text=True)
        with open(filepath, "w", encoding="utf-8") as fp:
            fp.write(m._repr_html_())
        del fp
        furi = f"file://{filepath}"
        logger.debug(f"furi: {furi}")
        webbrowser.open(furi, new=2, autoraise=True)
        return f"Opening map in default browser: {filepath}"

    def _cmd_merge(self, args):
        """
        Merge one local item into another
            > merge 1 2
              (merges content of local context 1 into local context 2)
        """
        if not self.manager.local:
            raise CommandError(
                "merge",
                "a local gazetteer must be created and populated or loaded first",
            )
        if len(args) != 2:
            raise UsageError(
                "merge",
                f"two local gazetteer context numbers must be provided as arguments; got {args}",
            )
        entries = list()
        for i in args:
            try:
                entries.append(self.local_context[i])
            except KeyError:
                raise ArgumentError(
                    "merge", f"Number {i} not in local gazetteer context."
                )
        return self.manager.local_merge(*entries)

    def _cmd_quit(self, args):
        """
        Quit interactive interface.
            > quit
            WARNING: unsaved data will be lost (use "save" first)
        """
        exit()

    def _context_lookup(self, args, command="_context_lookup"):
        """Do context lookups for various commands like raw and map"""
        if len(args) != 2:
            raise UsageError(
                command, f"invalid number of arguments (expected 2, got {len(args)})"
            )
        k = args[0]
        if k not in {"search", "local"}:
            raise UsageError(
                command, f"Invalid subcommand '{k}' (expected 'search' or 'local')"
            )
        elif k == "search":
            context = self.external_context
        elif k == "local":
            context = self.local_context
        i = args[1]
        try:
            str(int(i))
        except ValueError:
            raise ArgumentError(
                command, "Invalid context number (expected integer, got '{i}')"
            )
        try:
            v = context[i]
        except KeyError:
            if len(context) == 0:
                raise ArgumentError(
                    command,
                    f"No {k} context is defined, so context number {i} is out of range.",
                )
            else:
                raise ArgumentError(
                    command,
                    f"Context number {i} is out of range (current {k} context range = 1-{len(context)}.",
                )
        return v

    def _cmd_raw(self, args):
        """
        Show raw data view of an item in a context list
            > raw search 2
              (shows item 2 in the current search results list)
            > raw local 3
              (shows item 3 in the most recent local gazetteer listing or find results list)
        """
        if len(args) != 2:
            raise UsageError(
                "raw", f"invalid number of arguments (expected 2, got {len(args)})"
            )
        k = args[0]
        if k not in {"search", "local"}:
            raise UsageError(
                "raw", f"Invalid subcommand '{k}' (expected 'search' or 'local')"
            )
        elif k == "search":
            context = self.external_context
        elif k == "local":
            context = self.local_context
        i = args[1]
        try:
            str(int(i))
        except ValueError:
            raise ArgumentError(
                "raw", "Invalid context number (expected integer, got '{i}')"
            )
        try:
            v = context[i]
        except KeyError:
            if len(context) == 0:
                raise ArgumentError(
                    "raw",
                    f"No {k} context is defined, so context number {i} is out of range.",
                )
            else:
                raise ArgumentError(
                    "raw",
                    f"Context number {i} is out of range (current {k} context range = 1-{len(context)}.",
                )
        if not isinstance(v, dict):
            try:
                v = v.asdict()
            except AttributeError:
                pass
        return Pretty(v)

    def _cmd_search(self, args):
        """
        Conduct search in supported gazetteer(s).
            > search pleiades {keyword terms}
        """
        gname = args[0]
        try:
            results = self.manager.search(gname, args[1:])
        except ValueError as err:
            raise ArgumentError("search", str(err))
        msgs = [results["query"]]
        rows = list()
        self.external_context = dict()
        for i, hit in enumerate(results["hits"]):
            rows.append(
                (
                    f"{i+1}",
                    (
                        f"[bold]{hit['feature_type']}: "
                        f"{hit['title']}[/bold]\n"
                        f"[italic]{hit['uri']}[/italic]\n{hit['summary']}"
                    ),
                )
            )
            self.external_context[str(i + 1)] = hit
        msgs.append(
            self._table(
                ("context", "summary"),
                rows,
                title=f"Search hits: {len(results['hits'])}",
            )
        )
        return msgs

    def _cmd_usage(self, args):
        """
        Get usage for indicated command.
            > usage search
        """
        if not args:
            raise UsageError("usage", "missing command", "> usage search")
        cmd = args
        try:
            msg = getdoc(getattr(self, f"_cmd_{cmd}"))
        except AttributeError:
            raise ArgumentError(
                "usage",
                'Unrecognized command {cmd}. Try "help" to get a list of commands.',
            )
        else:
            msg = "\n".join([l.strip() for l in msg.split("\n")[1:]])
        return msg

    def _table(self, columns, rows, title=None):
        """Produce a rich table for output"""
        if title:
            t = Table(title=title, title_justify="left", leading=1)
        else:
            t = Table(leading=1)
        colors = ["magenta", "cyan"]
        for i, c in enumerate(columns):
            color = colors[i % len(colors)]
            t.add_column(c, style=color)
        for r in rows:
            t.add_row(*r)
        return t
