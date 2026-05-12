"""``slop rules`` — list all available rules with thresholds."""
from __future__ import annotations


def add_parser(subparsers) -> None:
    """Register the ``rules`` subcommand."""
    subparsers.add_parser("rules", help="List all available rules with thresholds")


def cmd_rules() -> int:
    """Run ``slop rules``."""
    from slop.linter import RULE_REGISTRY

    for rule in RULE_REGISTRY:
        enabled = "on" if rule.default_enabled else "off"
        threshold = getattr(rule, "threshold_label", "") or ""
        print(f"  {rule.name:32s} [{enabled:3s}] {threshold:10s} {rule.description}")
    return 0
