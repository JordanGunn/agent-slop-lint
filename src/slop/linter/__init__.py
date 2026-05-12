"""Linter package — entry-point class, Result, Slop finding type, rule registry.

Public exports:
  - ``Slop`` — the finding type
  - ``Result`` — the user-facing report from ``Linter.run()``
  - ``RULE_REGISTRY`` — aggregated registry of all built-in rules
  - ``RULES_BY_NAME`` — registry indexed by rule name
  - ``RULES_BY_CATEGORY`` — registry grouped by category (insertion order)
  - ``CATEGORIES`` — sorted list of category keys

``RULE_REGISTRY`` is composed from three substrate-aligned partial
registries: ``slop.structure.rules.STRUCTURAL_RULES`` (function /
class / package metrics + information.*), ``slop.lexicon.rules.LEXICAL_RULES``
(naming-discipline rules), and ``slop.linter.rules.CROSS_CUTTING_RULES``
(rules that need git churn or whole-tree analysis: ``structural.hotspots``,
``structural.orphans``).

``Linter`` itself is intentionally not re-exported: callers do
``from slop.linter.linter import Linter`` directly to avoid pulling
the dispatcher / rule loop into this lightweight import surface.
"""
from __future__ import annotations

from slop.lexicon.rules import LEXICAL_RULES
from slop.linter.rules import CROSS_CUTTING_RULES
from slop.structure.rules import STRUCTURAL_RULES

from .result import Result
from .slop import Slop
from .types import RuleDefinition

RULE_REGISTRY: list[RuleDefinition] = [
    *STRUCTURAL_RULES,
    *LEXICAL_RULES,
    *CROSS_CUTTING_RULES,
]

RULES_BY_NAME: dict[str, RuleDefinition] = {r.name: r for r in RULE_REGISTRY}

RULES_BY_CATEGORY: dict[str, list[RuleDefinition]] = {}
for _rule in RULE_REGISTRY:
    RULES_BY_CATEGORY.setdefault(_rule.category, []).append(_rule)

CATEGORIES: list[str] = sorted(RULES_BY_CATEGORY.keys())

__all__ = [
    "CATEGORIES",
    "CROSS_CUTTING_RULES",
    "LEXICAL_RULES",
    "Result",
    "RULE_REGISTRY",
    "RULES_BY_CATEGORY",
    "RULES_BY_NAME",
    "STRUCTURAL_RULES",
    "Slop",
]
