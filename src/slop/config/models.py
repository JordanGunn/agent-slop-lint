"""Config-file dataclasses.

``Config`` is what ``Linter.run()`` consumes — the merged result of
config-file discovery + defaults. ``Config.rule_config(name)`` returns
the per-rule ``RuleConfig`` (from ``slop.linter.rule_config``); missing
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

from slop.linter.rule_config import RuleConfig


@dataclass
class Waiver:
    """Scoped exception for known, bounded lint findings."""

    id: str
    path: str
    rule: str
    reason: str
    allow_up_to: float | int | None = None
    expires: str | None = None


@dataclass
class Config:
    """Top-level slop configuration."""

    root: str = "."
    languages: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)
    waivers: list[Waiver] = field(default_factory=list)
    rules: dict[str, RuleConfig] = field(default_factory=dict)
    config_path: Path | None = None

    def rule_config(self, category: str) -> RuleConfig:
        """Get the RuleConfig for a category, falling back to defaults."""
        return self.rules.get(category, RuleConfig())
