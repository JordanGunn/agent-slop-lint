"""Shared CLI helpers — common args, lint runner, preflight error block.

Private to the cli package. Consumed by ``cmd.py`` (lint) and
``check.py``.
"""
from __future__ import annotations

import argparse
import sys

import json

from slop.cli.color import bold, dim, red
from slop.config.loader import load_config
from slop.linter import format as _format
from slop.linter.linter import Linter
from slop.preflight import MissingBinary, check_required_binaries


def register_subcommand(
    subparsers, name: str, *, help: str, description: str,
) -> argparse.ArgumentParser:
    """Register a subcommand with the standard help/description signature.

    Collapses the boilerplate ``subparsers.add_parser(name, help=..., description=...)``
    pattern repeated across CLI command modules.
    """
    return subparsers.add_parser(name, help=help, description=description)


def add_common_args(parser: argparse.ArgumentParser) -> None:
    """Common run-flags shared by ``lint`` and ``check``."""
    parser.add_argument(
        "--root", type=str, default=None,
        help="Repository root (overrides config)",
    )
    parser.add_argument(
        "--config", type=str, default=None, dest="config_path",
        help="Path to config file (overrides auto-discovery)",
    )
    parser.add_argument(
        "--output", choices=["human", "json", "quiet"], default="human",
        help="Output format (default: human)",
    )
    parser.add_argument(
        "--max-violations", type=int, default=_format.DEFAULT_MAX_VIOLATIONS, metavar="N",
        help=f"Max violations shown per rule (default: {_format.DEFAULT_MAX_VIOLATIONS}, 0 = unlimited)",
    )
    parser.add_argument(
        "--no-color", action="store_true",
        help="Disable colored output",
    )


def load_and_run(args: argparse.Namespace, **lint_kwargs) -> int:
    """Shared logic for lint and check: load config, run linter, format output."""
    try:
        config = load_config(
            config_path=getattr(args, "config_path", None),
            root=getattr(args, "root", None),
        )
    except Exception as e:
        print(f"slop: config error: {e}", file=sys.stderr)
        return 2

    missing = check_required_binaries(config)
    if missing:
        _print_missing_binaries(missing)
        return 2

    display_root = args.root or config.root
    if args.root:
        config.root = args.root

    result = Linter(config).run(display_root=display_root, **lint_kwargs)

    max_v = getattr(args, "max_violations", _format.DEFAULT_MAX_VIOLATIONS)
    if max_v == 0:
        max_v = 999999

    if args.output == "json":
        print(json.dumps(result.json(), indent=2))
    elif args.output == "quiet":
        print(result.pretty(verbose=False))
    else:
        print(result.pretty(max_violations=max_v))

    if result.verdict == "error":
        return 2
    if result.verdict == "fail":
        return 1
    return 0


def _print_missing_binaries(missing: list[MissingBinary]) -> None:
    """Render a preflight error block to stderr when required binaries are absent."""
    header = red(bold("slop: missing required system binaries"))
    print(header, file=sys.stderr)
    print("", file=sys.stderr)
    for m in missing:
        rules_str = ", ".join(m.rules)
        print(f"  {red(chr(0x2717))} {bold(m.name)} — needed by {rules_str}", file=sys.stderr)
        if m.install:
            print(f"      install: {m.install}", file=sys.stderr)
    print("", file=sys.stderr)
    hint = dim("Install the missing binaries and retry. Run 'slop doctor' to recheck.")
    print(hint, file=sys.stderr)
