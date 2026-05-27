"""Linter package — entry-point class, Result, Slop finding type, rule registry.

Public exports:
  - ``Slop`` — the finding type
  - ``Result`` — the user-facing report from ``Linter.run()``
  - ``RULE_REGISTRY`` — every rule slop ships, flat (defined in
    ``slop.linter.rules``)
  - ``RULES_BY_NAME`` — registry indexed by rule name
  - ``RULES_BY_CATEGORY`` — registry grouped by category (insertion order)
  - ``CATEGORIES`` — sorted list of category keys

``Linter`` itself is intentionally not re-exported: callers do
``from slop.linter.linter import Linter`` directly to avoid pulling
the dispatcher / rule loop into this lightweight import surface.
"""
from __future__ import annotations

from .result import Result
from .slop import Slop
from .types import RuleDefinition

# The aggregated views (RULE_REGISTRY / RULES_BY_NAME / RULES_BY_CATEGORY /
# CATEGORIES) are lazy-loaded via module-level __getattr__. Lazy access
# defers the rules-package import (which itself imports ~30 rule modules)
# until first use, keeping this module a lightweight entrypoint.

__all__ = [
    "CATEGORIES",
    "Result",
    "RULE_REGISTRY",
    "RULES_BY_CATEGORY",
    "RULES_BY_NAME",
    "Slop",
]


_LAZY_NAMES = frozenset({
    "RULE_REGISTRY", "RULES_BY_NAME", "RULES_BY_CATEGORY", "CATEGORIES",
})


def __getattr__(name: str):
    if name not in _LAZY_NAMES:
        raise AttributeError(name)
    import sys

    from slop.linter.rules import RULE_REGISTRY

    rules_by_name: dict[str, RuleDefinition] = {r.name: r for r in RULE_REGISTRY}
    rules_by_category: dict[str, list[RuleDefinition]] = {}
    for rule in RULE_REGISTRY:
        rules_by_category.setdefault(rule.category, []).append(rule)
    categories: list[str] = sorted(rules_by_category.keys())

    mod = sys.modules[__name__]
    mod.RULE_REGISTRY = RULE_REGISTRY
    mod.RULES_BY_NAME = rules_by_name
    mod.RULES_BY_CATEGORY = rules_by_category
    mod.CATEGORIES = categories
    return getattr(mod, name)
