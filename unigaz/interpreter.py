#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interpreter to provide a clean API for interacting with ocmnponents
"""

from inspect import getdoc
import logging
from sqlite3 import NotSupportedError
from rich.table import Table
from rich.pretty import Pretty
import shlex
import traceback
from unigaz.manager import Manager
from unigaz.web import SearchParameterError


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

    def _cmd_local(self, args):
        """
        Work with local gazetteers
            > local create My Sites
              creates a new local gazetteer named 'My Sites'
            > local accession 7
              make a new entry in the local gazetteer on the basis of context number 7
        """
        real_cmd = f"_real_cmd_local_{args[0]}"
        try:
            return getattr(self, real_cmd)(args[1:])
        except AttributeError:
            return f"Unrecognized command 'local {args[0]}'"

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

    def _cmd_quit(self, args):
        """
        Quit interactive interface.
            > quit
            WARNING: unsaved data will be lost (use "save" first)
        """
        exit()

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

    def _real_cmd_local_accession(self, args):
        i = args[0]
        try:
            hit = self.external_context[args[0]]
        except KeyError:
            raise ArgumentError(f"Number {args} not in external search context.")
        result = self.manager.local_accession(hit)
        return f"Created {result.__class__.__name__} '{result.title}' from external source.'"

    def _real_cmd_local_create(self, args):
        """
        Create a local gazetteer.
        """
        results = self.manager.local_create(" ".join(args))
        return results

    def _real_cmd_local_list(self, args):
        """
        List contents of the local gazetteer.
        """
        content_list = self.manager.local_list(args)
        content_list.sort(key=lambda o: o.sort_key)
        rows = list()
        self.local_context = dict()
        for i, o in enumerate(content_list):
            row = (f"{i+1}", f"{o.__class__.__name__}: {o.title}\n{o.description}")
            rows.append(row)
            self.local_context[str(i + 1)] = o
        return self._table(
            title=f"{self.manager.local.title}: {len(content_list)} items",
            columns=["context", "summary"],
            rows=rows,
        )

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
