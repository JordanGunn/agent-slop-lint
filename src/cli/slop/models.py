"""Core data models for slop."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Config models
# ---------------------------------------------------------------------------


@dataclass
class RuleConfig:
    """Per-rule configuration extracted from the slop config file."""

    enabled: bool = True
    severity: str = "error"           # "error" | "warning" | "off"
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class SlopConfig:
    """Top-level slop configuration."""

    root: str = "."
    languages: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)
    rules: dict[str, RuleConfig] = field(default_factory=dict)
    config_path: Path | None = None

    def rule_config(self, category: str) -> RuleConfig:
        """Get the RuleConfig for a category, falling back to defaults."""
        return self.rules.get(category, RuleConfig())


# ---------------------------------------------------------------------------
# Result models
# ---------------------------------------------------------------------------


@dataclass
class Violation:
    """A single linter violation."""

    rule: str                          # e.g. "complexity.cyclomatic"
    file: str                          # relative path
    line: int | None = None
    symbol: str | None = None
    message: str = ""
    severity: str = "error"            # "error" | "warning" | "info"
    value: float | int | None = None   # the measured value
    threshold: float | int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RuleResult:
    """Result from running one rule."""

    rule: str                          # e.g. "complexity.cyclomatic"
    status: str = "pass"               # "pass" | "fail" | "skip" | "error"
    violations: list[Violation] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


@dataclass
class LintResult:
    """Aggregated result from running all rules."""

    version: str
    root: str
    languages: list[str]
    display_root: str = ""          # original root before resolve (for display)
    rule_results: dict[str, RuleResult] = field(default_factory=dict)
    rules_checked: int = 0
    rules_skipped: int = 0
    violation_count: int = 0
    advisory_count: int = 0
    result: str = "pass"               # "pass" | "fail" | "error"


# ---------------------------------------------------------------------------
# Rule definition
# ---------------------------------------------------------------------------

# Type alias for a rule's run function.
# Signature: (root: Path, rule_config: RuleConfig, slop_config: SlopConfig) -> RuleResult
RuleRunner = Callable[..., RuleResult]


@dataclass(frozen=True)
class RuleDefinition:
    """Definition of a single linter rule."""

    name: str                          # e.g. "complexity.cyclomatic"
    category: str                      # e.g. "complexity"
    description: str
    default_severity: str = "error"    # "error" | "warning" | "off"
    default_enabled: bool = True
    threshold_label: str = ""       # e.g. "CCX > 10" for slop rules display
    run: RuleRunner = field(default=lambda *a, **kw: RuleResult(rule=""))  # type: ignore[assignment]
