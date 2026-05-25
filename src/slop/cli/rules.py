"""``slop rules`` — list all available rules with thresholds.

The ``--scope`` filter restricts the listing to rules that emit at the
given scope (``function``, ``class``, ``module``, ``parameter``,
``package``). Without ``--scope`` all rules are listed, including
cross-cutting and cluster/multi-scope ones (``hotspots``, ``deps``,
``orphans``, ``redundancy``, ``duplication``, ``lexical.*``).
"""
from __future__ import annotations

import argparse


_SCOPE_CHOICES = ("function", "class", "module", "parameter", "package")


def add_parser(subparsers) -> None:
    """Register the ``rules`` subcommand."""
    p = subparsers.add_parser(
        "rules",
        help="List all available rules with thresholds",
    )
    p.add_argument(
        "--scope",
        choices=_SCOPE_CHOICES,
        default=None,
        help=(
            "Filter to rules that emit at this scope. "
            "Without --scope, all rules are listed (including "
            "cross-cutting and lexical.* exempt rules)."
        ),
    )


def cmd_rules(args: argparse.Namespace | None = None) -> int:
    """Run ``slop rules``."""
    from slop.linter import RULE_REGISTRY

    scope_filter: str | None = getattr(args, "scope", None) if args else None

    for rule in RULE_REGISTRY:
        if scope_filter is not None:
            scopes = getattr(rule, "scopes", ()) or ()
            if scope_filter not in scopes:
                continue
        enabled = "on" if rule.default_enabled else "off"
        threshold = getattr(rule, "threshold_label", "") or ""
        scopes = getattr(rule, "scopes", ()) or ()
        scopes_label = ",".join(scopes) if scopes else "—"
        print(
            f"  {rule.name:30s} "
            f"[{enabled:3s}] "
            f"scope=[{scopes_label:30s}] "
            f"{threshold:15s} "
            f"{rule.description}"
        )
    return 0
