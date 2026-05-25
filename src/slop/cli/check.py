"""``slop check <target>`` — filter rules by category, suite, or rule name."""
from __future__ import annotations

import argparse
import sys

from .common import add_common_args, load_and_run


def add_parser(subparsers) -> None:
    """Register the ``check`` subcommand."""
    parser = subparsers.add_parser(
        "check", help="Run rules for a specific category or rule",
    )
    parser.add_argument(
        "target", type=str,
        help=(
            "Category (e.g. 'complexity'), prefix table "
            "(e.g. 'class'), or rule (e.g. 'complexity.cyclomatic')"
        ),
    )
    add_common_args(parser)


def cmd_check(args: argparse.Namespace) -> int:
    """Run ``slop check <target>``."""
    from slop.linter import CATEGORIES, RULE_REGISTRY, RULES_BY_NAME

    target = args.target

    if target in RULES_BY_NAME:
        return load_and_run(args, filter_rule=target)
    if any(r.name.startswith(target + ".") for r in RULE_REGISTRY):
        return load_and_run(args, filter_rule=target)

    known_categories = {r.category for r in RULE_REGISTRY}
    if target in known_categories:
        return load_and_run(args, filter_category=target)
    if any(c.startswith(target + ".") for c in known_categories):
        return load_and_run(args, filter_category=target)

    available = ", ".join(sorted(CATEGORIES))
    print(
        f"slop: unknown rule or category '{target}'\n"
        f"Available categories: {available}\n"
        f"Run 'slop rules' for full list.",
        file=sys.stderr,
    )
    return 2
