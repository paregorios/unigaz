#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Command-line interface for meek
"""

from airtight.cli import configure_commandline
from unigaz.interpreter import Interpreter, ArgumentError, UsageError, CommandError
from textnorm import normalize_space, normalize_unicode
import logging
from rich.console import Console
import readline
import shlex


logger = logging.getLogger(__name__)

DEFAULT_LOG_LEVEL = logging.WARNING
OPTIONAL_ARGUMENTS = [
    [
        "-l",
        "--loglevel",
        "NOTSET",
        "desired logging level ("
        + "case-insensitive string: DEBUG, INFO, WARNING, or ERROR",
        False,
    ],
    ["-v", "--verbose", False, "verbose output (logging level == INFO)", False],
    [
        "-w",
        "--veryverbose",
        False,
        "very verbose output (logging level == DEBUG)",
        False,
    ],
]
POSITIONAL_ARGUMENTS = [
    # each row is a list with 3 elements: name, type, help
]


def norm(s: str):
    return normalize_space(normalize_unicode(s))


def interact():
    c = Console(record=True)
    i = Interpreter()
    c.print("[bold blue]UniGaz: Tools for working with digital gazetteers[/bold blue]")
    c.print("[italic blue]type 'help' for a list of commands[/italic blue]")
    while (
        True
    ):  # keep taking commands until something breaks us out to finish the program
        try:
            s = norm(c.input("[bold blue]> [/bold blue]"))
        except KeyboardInterrupt:
            r = i.parse("quit")
        else:
            try:
                r = i.parse(s)
            except NotImplementedError as err:
                c.print(f"[orange][bold]NOT IMPLEMENTED: [/bold]{str(err)}[/orange]")
            except (UsageError, ArgumentError, CommandError) as err:
                c.print(f"[orange][bold]ERROR: [/bold]{str(err)}[/orange]")
            else:
                if isinstance(r, list):
                    for l in r:
                        c.print(l)
                else:
                    c.print(r)


def main(**kwargs):
    """
    main function
    """
    # logger = logging.getLogger(sys._getframe().f_code.co_name)
    interact()


if __name__ == "__main__":
    main(
        **configure_commandline(
            OPTIONAL_ARGUMENTS, POSITIONAL_ARGUMENTS, DEFAULT_LOG_LEVEL
        )
    )
