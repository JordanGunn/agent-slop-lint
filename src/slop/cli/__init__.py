"""slop CLI.

Primitives (read-only views over the layers): ``ast`` / ``tree`` / ``find`` / ``lexicon`` /
``deps`` / ``vocab`` / ``shape`` / ``hotspots``. Lint: ``lint`` / ``check`` / ``rules``.
Inference: ``infer``. Vocabulary: ``ontology``. Housekeeping: ``doctor`` / ``init`` / ``skill``.

The primitives answer questions and exit 0 whenever they answered (an empty result is an
answer); 2 means the question could not be answered. The lint commands exit 0 with no
violations, 1 with any, 2 on error.

Each module registers its own commands, each with the function it runs as ``run``.
"""
from __future__ import annotations

import argparse
import sys
from importlib.metadata import PackageNotFoundError, version as _pkg_version

from . import ast, config, deps, doctor, find, hotspots, infer, lexicon, lint, ontology, shape, skill, tree

#: in the order ``slop --help`` lists them
_COMMANDS = (lint, doctor, config, ast, lexicon, deps, find, tree, ontology, shape, hotspots, infer, skill)


def version() -> str:
    """The installed distribution version, or ``unknown`` when running from a source
    tree that was never installed (no dist metadata to read)."""
    try:
        return _pkg_version("agent-slop-lint")
    except PackageNotFoundError:
        return "unknown"


def parser() -> argparse.ArgumentParser:
    """Every command, each with the function it runs as ``run``."""
    root = argparse.ArgumentParser(prog="slop", description="a linter and code-structure query tool")
    root.add_argument("--version", action="version", version=f"slop {version()}")
    sub = root.add_subparsers(dest="command", required=True)
    for commands in _COMMANDS:
        commands.register(sub)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        return args.run(args)
    except Exception as exc:  # noqa: BLE001 — top-level boundary: any failure is exit 2
        print(f"slop: error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
