"""``slop schema`` — print the config-file JSON Schema.

Thin CLI wrapper around ``slop.schemas.config.generate()``.
"""
from __future__ import annotations

import json


def add_parser(subparsers) -> None:
    """Register the ``schema`` subcommand."""
    subparsers.add_parser("schema", help="Print config schema as JSON")


def cmd_schema() -> int:
    """Run ``slop schema``."""
    from slop.schemas.config import generate

    print(json.dumps(generate(), indent=2))
    return 0
