"""Config dataclasses — what the loader produces, what rules consume."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class RuleConfig:
    """Per-rule configuration extracted from the slop config file."""

    enabled: bool = True
    severity: str = "error"           # "error" | "warning" | "off"
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class WaiverConfig:
    """Scoped exception for known, bounded lint findings."""

    id: str
    path: str
    rule: str
    reason: str
    allow_up_to: float | int | None = None
    expires: str | None = None


@dataclass
class SlopConfig:
    """Top-level slop configuration."""

    root: str = "."
    languages: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)
    waivers: list[WaiverConfig] = field(default_factory=list)
    rules: dict[str, RuleConfig] = field(default_factory=dict)
    config_path: Path | None = None

    def rule_config(self, category: str) -> RuleConfig:
        """Get the RuleConfig for a category, falling back to defaults."""
        return self.rules.get(category, RuleConfig())
