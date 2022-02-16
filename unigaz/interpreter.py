#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interpreter to provide a clean API for interacting with ocmnponents
"""

from inspect import getdoc
import logging
from sqlite3 import NotSupportedError
from rich.table import Table
import shlex
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
        aliases = {"?": "help", "g": "gazetteer", "q": "quit"}
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

    def _cmd_search(self, args):
        """
        Conduct search in supported gazetteer(s).
            > search pleiades {keyword terms}
        """
        gname = args[0]
        if self.manager.supported(gname):
            g = self.manager.gazetteers[gname]
            kwargs = {"text": set()}
            for arg in args[1:]:
                parts = arg.split(":")
                if len(parts) == 1:
                    kwargs["text"].add(parts[0])
                elif len(parts) == 2:
                    kwargs[parts[0]] = parts[1]
                else:
                    raise ArgumentError("search", f"'{arg}' in '{args}'.")
            if len(kwargs["text"]) == 0:
                kwargs.pop("text")
            try:
                results = g.search(**kwargs)
            except SearchParameterError as err:
                raise CommandError("search", str(err))
            msgs = [results["query"]]
            rows = list()
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
            msgs.append(
                self._table(
                    ("context", "summary"),
                    rows,
                    title=f"Search hits: {len(results['hits'])}",
                )
            )
            return msgs
        else:
            raise UsageError("search", f"Gazetteer '{gname}' is not supported.")

    def _cmd_quit(self, args):
        """
        Quit interactive interface.
            > quit
            WARNING: unsaved data will be lost (use "save" first)
        """
        exit()

    def _table(self, columns, rows, title=None):
        if title:
            t = Table(title=title, title_justify="left", leading=1)
        else:
            t = Table(leading=1)
        colors = ["cyan", "magenta"]
        for i, c in enumerate(columns):
            color = colors[(i + 1) % len(colors)]
            t.add_column(c, style=color)
        for r in rows:
            t.add_row(*r)
        return t