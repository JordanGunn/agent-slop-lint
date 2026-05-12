"""``slop init [profile]`` — generate a .slop.toml config file."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from slop.config import generate_default_config


def add_parser(subparsers) -> None:
    """Register the ``init`` subcommand."""
    parser = subparsers.add_parser(
        "init", help="Generate a .slop.toml config file",
        description="Generate a .slop.toml config file with a named profile.",
    )
    parser.add_argument(
        "profile", nargs="?", default="default",
        choices=["default", "lax", "strict"],
        help="Config profile: default (balanced), lax (legacy/gradual), strict (greenfield)",
    )


def cmd_init(profile: str = "default") -> int:
    """Run ``slop init``."""
    target = Path.cwd() / ".slop.toml"
    if target.exists():
        print(f"slop: {target} already exists", file=sys.stderr)
        return 1
    target.write_text(generate_default_config(profile))
    print(f"Created {target} (profile: {profile})")
    return 0
