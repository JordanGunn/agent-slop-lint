"""Concrete rules. ``RULE_REGISTRY`` is the single flat list the dispatcher and
config consume. Each entry is a stateless ``Rule`` instance; its ``name`` and
``altitudes`` are class-level, and ``default_config`` ships its defaults.

This is the validation slice (one verdict, one observation, one REVIEW verdict —
exercising every cell of the finding ontology). Remaining rules port against this
proven contract, one at a time.
"""
from __future__ import annotations

from ..rule import Rule
from .call_islands import CallIslandsRule
from .cyclomatic import CyclomaticRule
from .token_distribution import TokenDistributionRule

RULE_REGISTRY: list[Rule] = [
    CyclomaticRule(),
    TokenDistributionRule(),
    CallIslandsRule(),
]

__all__ = ["RULE_REGISTRY", "CyclomaticRule", "TokenDistributionRule", "CallIslandsRule"]
