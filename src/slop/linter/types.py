"""Linter-result types — what rules emit and the engine aggregates."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .slop import Slop


@dataclass
class RuleResult:
    """Result from running one rule."""

    rule: str
    status: str = "pass"
    violations: list[Slop] = field(default_factory=list)
    waived_violations: list[Slop] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


# Type alias for rule run functions.
RuleRunner = Callable[..., RuleResult]
"""(view: Structure | Lexicon, rule_config: RuleConfig, slop_config: SlopConfig) -> RuleResult"""


@dataclass(frozen=True)
class RuleDefinition:
    """Definition of a single linter rule."""

    name: str
    category: str
    description: str
    default_severity: str = "error"
    default_enabled: bool = True
    threshold_label: str = ""
    run: RuleRunner = field(default=lambda *a, **kw: RuleResult(rule=""))  # type: ignore[assignment]
