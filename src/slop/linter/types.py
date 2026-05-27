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
"""(view: Structure | Lexicon, rule_config: Rule, slop_config: Config) -> RuleResult"""


@dataclass(frozen=True)
class RuleDefinition:
    """Definition of a single linter rule.

    The ``scopes`` field declares which emission scopes a rule supports
    (``function``, ``class``, ``module``, ``parameter``, ``package``).
    Empty tuple means scope-agnostic (cross-cutting rules: cycles,
    hotspots, orphans, clone clusters, redundancy pairs). The rule body
    iterates its declared scopes at runtime and consults the per-scope
    threshold under ``rule_config.params['thresholds'][scope]``; missing
    scope key means the rule skips that scope.
    """

    name: str
    category: str
    description: str
    default_severity: str = "error"
    default_enabled: bool = True
    threshold_label: str = ""
    run: RuleRunner = field(default=lambda *a, **kw: RuleResult(rule=""))  # type: ignore[assignment]
    scopes: tuple[str, ...] = ()
