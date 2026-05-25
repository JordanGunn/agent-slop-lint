"""Linter package — entry-point class, Result, Slop finding type, rule registry.

Public exports:
  - ``Slop`` — the finding type
  - ``Result`` — the user-facing report from ``Linter.run()``
  - ``RULE_REGISTRY`` — aggregated registry of all built-in rules
  - ``RULES_BY_NAME`` — registry indexed by rule name
  - ``RULES_BY_CATEGORY`` — registry grouped by category (insertion order)
  - ``CATEGORIES`` — sorted list of category keys

``RULE_REGISTRY`` is composed from three substrate-aligned partial
registries: ``slop.structure.metrics.STRUCTURAL_RULES`` (function /
class / package metrics + information.*), ``slop.lexicon.metrics.LEXICAL_RULES``
(naming-discipline rules), and ``slop.linter.rules.CROSS_CUTTING_RULES``
(rules that need git churn or whole-tree analysis: ``hotspots``,
``orphans``).

``Linter`` itself is intentionally not re-exported: callers do
``from slop.linter.linter import Linter`` directly to avoid pulling
the dispatcher / rule loop into this lightweight import surface.
"""
from __future__ import annotations

from .result import Result
from .slop import Slop
from .types import RuleDefinition

# The aggregated registries (RULE_REGISTRY / RULES_BY_NAME /
# RULES_BY_CATEGORY / CATEGORIES + the three per-substrate registries
# they're composed from) are lazy-loaded via module-level __getattr__.
# Lazy access defers each rules-package import until first use, keeping
# this module a lightweight entrypoint.

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


_LAZY_NAMES = frozenset({
    "STRUCTURAL_RULES", "LEXICAL_RULES", "CROSS_CUTTING_RULES",
    "RULE_REGISTRY", "RULES_BY_NAME", "RULES_BY_CATEGORY", "CATEGORIES",
})


def __getattr__(name: str):
    if name not in _LAZY_NAMES:
        raise AttributeError(name)
    import sys

    from slop.lexicon.metrics import LEXICAL_RULES
    from slop.linter.rules import CROSS_CUTTING_RULES
    from slop.structure.metrics import STRUCTURAL_RULES

    rule_registry: list[RuleDefinition] = [
        *STRUCTURAL_RULES, *LEXICAL_RULES, *CROSS_CUTTING_RULES,
    ]
    rules_by_name: dict[str, RuleDefinition] = {r.name: r for r in rule_registry}
    rules_by_category: dict[str, list[RuleDefinition]] = {}
    for rule in rule_registry:
        rules_by_category.setdefault(rule.category, []).append(rule)
    categories: list[str] = sorted(rules_by_category.keys())

    mod = sys.modules[__name__]
    mod.STRUCTURAL_RULES = STRUCTURAL_RULES
    mod.LEXICAL_RULES = LEXICAL_RULES
    mod.CROSS_CUTTING_RULES = CROSS_CUTTING_RULES
    mod.RULE_REGISTRY = rule_registry
    mod.RULES_BY_NAME = rules_by_name
    mod.RULES_BY_CATEGORY = rules_by_category
    mod.CATEGORIES = categories
    return getattr(mod, name)
