"""Composition root for slop.

Thin entry point. Imports the CLI dispatcher lazily so ``slop --help``
doesn't pay the cost of pulling in tree-sitter and the rule registry.

See ``docs/planning/linter.md`` for the locked design.
"""
from __future__ import annotations


def main(argv: list[str] | None = None) -> int:
    """Entry point for the ``slop`` console script."""
    from slop.cli import main as cli_main
    return cli_main(argv)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
