"""``slop schema`` — print the config-file JSON Schema."""
from __future__ import annotations

import json


def add_parser(subparsers) -> None:
    """Register the ``schema`` subcommand."""
    parser = subparsers.add_parser("schema", help="Print config schema as JSON")
    parser.add_argument(
        "--version",
        default=None,
        help="Schema version to print (default: latest)",
    )


def cmd_schema(version: str | None = None) -> int:
    """Run ``slop schema``."""
    from slop.config import schema

    print(json.dumps(schema.load(version or schema.LATEST), indent=2))
    return 0
