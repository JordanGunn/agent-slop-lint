"""Config-file dataclasses.

``Config`` is what ``Linter.run()`` consumes — the merged result of
config-file discovery + defaults. ``Config.rule_config(name)`` returns
the per-rule ``Rule`` (from ``slop.linter.rule_config``); missing
rules fall back to an empty default.

``Waiver`` is a scoped exception for known, bounded lint findings: it
suppresses findings for a specific (rule, path) tuple. Used sparingly
to keep exceptional findings visible without weakening global
thresholds. ``allow_up_to`` is a local relaxation; ``expires`` is an
optional ISO date after which the waiver is treated as stale and
surfaced as advisory.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from slop.config.waiver import Waiver
from slop.linter.rule import Rule


@dataclass
class Config:
    """Top-level slop configuration."""

    root: str = "."
    languages: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)
    waivers: list[Waiver] = field(default_factory=list)
    rules: dict[str, Rule] = field(default_factory=dict)
    config_path: Path | None = None

    def rule_config(self, category: str) -> Rule:
        """Get the Rule for a category, falling back to defaults."""
        return self.rules.get(category, Rule())
