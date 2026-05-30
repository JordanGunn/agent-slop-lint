"""Config-file dataclasses.

``Config`` is what ``Linter.run()`` consumes — the merged result of
config-file discovery + defaults. ``Config.rule_config(name)`` returns
the per-rule ``Rule`` (from ``slop.linter.rule``); missing rules fall
back to an empty default.

``ignore`` is the global exemption surface: a scope-keyed map of declared
names (``classes`` / ``functions`` / ``modules`` / ``packages``) that
suppresses any matching finding across every rule. Per-rule exemptions
live under ``[rules.<rule>.ignore]`` (carried in that rule's ``params``).
A finding is suppressed when its ``symbol`` appears in the ignore list
for its scope — a plain membership check, scope-precise (ignoring a
class never blinds its methods) and rule-precise when scoped to a rule.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from slop.linter.rule import Rule


@dataclass
class Config:
    """Top-level slop configuration."""

    root: str = "."
    languages: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)
    ignore: dict[str, list[str]] = field(default_factory=dict)
    rules: dict[str, Rule] = field(default_factory=dict)
    config_path: Path | None = None

    def rule_config(self, name: str) -> Rule:
        """Get the ``Rule`` for a rule *name* (e.g. ``complexity.cyclomatic``).

        The ``rules`` dict is keyed by ``RuleDefinition.name``, NOT by
        category — a rule whose name differs from its category (the
        ``complexity.*`` family) must be looked up by name or it silently
        receives the empty-default ``Rule()`` (no thresholds → no-op).
        Missing names fall back to an empty default so rules absent from
        the config still run on their own internal defaults.
        """
        return self.rules.get(name, Rule())
