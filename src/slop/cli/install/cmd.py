"""Root command for the ``slop install`` subcommand package.

Per the cli-package convention: every CLI package has a ``cmd.py``
that wires the root parser and dispatch for the bounding package.
This file does that for ``slop install``.
"""
from __future__ import annotations

import argparse
import sys

from . import hook, skill


def add_parser(subparsers) -> None:
    """Register the ``install`` subcommand with nested install targets."""
    from slop.cli.common import register_subcommand
    install_parser = register_subcommand(
        subparsers, "install",
        help="Install slop integrations (hook, skill)",
        description="Install slop integrations into the local repository or filesystem.",
    )
    install_sub = install_parser.add_subparsers(
        dest="install_target", metavar="<target>",
    )
    hook.add_parser(install_sub)
    skill.add_parser(install_sub)


def dispatch(args: argparse.Namespace) -> int:
    """Dispatch ``slop install <target>``."""
    target = getattr(args, "install_target", None)
    if target == "hook":
        return hook.cmd_hook(disable=getattr(args, "disable", False))
    if target == "skill":
        return skill.cmd_skill(args.directory)
    print(
        "slop install: specify a target (hook | skill)\n"
        "Run 'slop install --help' for details.",
        file=sys.stderr,
    )
    return 2
