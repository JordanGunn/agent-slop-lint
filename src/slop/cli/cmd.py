"""Root command for the ``slop`` CLI.

Per the cli-package convention: every CLI package has a ``cmd.py``
that wires the root parser and dispatch for the bounding package.
This file does that for ``slop``.

It also implements the ``lint`` subcommand — the default behaviour
when ``slop`` is run with no arguments. Other subcommands live in
sibling modules (``check.py``, ``init.py``, ``rules.py``, etc.).
"""
from __future__ import annotations

import argparse

from slop import __version__
from slop.cli.color import set_color

from slop.linter import format as _format
from . import check, doctor, init, rules, schema
from .common import add_common_args, load_and_run
from .install import cmd as install_cmd


def create_parser() -> argparse.ArgumentParser:
    """Build the ``slop`` argument parser with all subcommands registered."""
    parser = argparse.ArgumentParser(
        prog="slop",
        description="slop — agentic code quality linter",
        epilog="""\
Commands:
  lint         Run all enabled rules (default)
  check        Run rules for a specific category or rule
  init         Generate a default .slop.toml config file
  rules        List all available rules with thresholds
  schema       Print JSON schema of the config
  doctor       Check that required system binaries are installed
  install      Install slop integrations (hook, skill)

Examples:
  slop lint
  slop lint --root ./src --output json
  slop check complexity
  slop check complexity.cyclomatic
  slop init                       # default profile
  slop install hook               # git pre-commit hook
  slop install skill ./my-agent   # bundle skill files
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"slop {__version__}")

    subparsers = parser.add_subparsers(dest="command", metavar="<command>")

    # lint (the root/default command)
    lint_parser = subparsers.add_parser(
        "lint", help="Run all enabled rules against the codebase",
    )
    add_common_args(lint_parser)

    # Other top-level subcommands.
    check.add_parser(subparsers)
    init.add_parser(subparsers)
    rules.add_parser(subparsers)
    schema.add_parser(subparsers)
    doctor.add_parser(subparsers)
    install_cmd.add_parser(subparsers)

    return parser


def cmd_lint(args: argparse.Namespace) -> int:
    """Run ``slop lint``."""
    return load_and_run(args)


def main(argv: list[str] | None = None) -> int:
    """Entry point for ``slop`` (called from ``slop.app:main``)."""
    parser = create_parser()
    args = parser.parse_args(argv)

    if getattr(args, "no_color", False):
        set_color(False)

    # Default to ``lint`` when no subcommand is given.
    if args.command is None:
        args.command = "lint"
        args.root = None
        args.config_path = None
        args.output = "human"
        args.max_violations = _format.DEFAULT_MAX_VIOLATIONS
        args.no_color = False

    dispatch = {
        "lint":    cmd_lint,
        "check":   check.cmd_check,
        "init":    lambda a: init.cmd_init(getattr(a, "profile", "default")),
        "rules":   rules.cmd_rules,
        "schema":  lambda a: schema.cmd_schema(getattr(a, "version", None)),
        "doctor":  lambda _: doctor.cmd_doctor(),
        "install": install_cmd.dispatch,
    }

    handler = dispatch.get(args.command)
    if handler is None:
        parser.print_help()
        return 0
    return handler(args)
