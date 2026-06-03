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
from .class_shape import ClassShapeRule
from .cognitive import CognitiveRule
from .combinatorial import CombinatorialRule
from .cyclomatic import CyclomaticRule
from .dependency_cycles import DependencyCyclesRule
from .duplication import DuplicationRule
from .escape_hatches import EscapeHatchesRule
from .god_module import GodModuleRule
from .hidden_mutators import HiddenMutatorsRule
from .orphans import OrphansRule
from .rigidity import RigidityRule
from .sentinels import SentinelsRule
from .token_distribution import TokenDistributionRule
from .uselessness import UselessnessRule

RULE_REGISTRY: list[Rule] = [
    CyclomaticRule(),
    CognitiveRule(),
    CombinatorialRule(),
    GodModuleRule(),
    EscapeHatchesRule(),
    DuplicationRule(),
    DependencyCyclesRule(),
    RigidityRule(),
    UselessnessRule(),
    SentinelsRule(),
    HiddenMutatorsRule(),
    OrphansRule(),
    ClassShapeRule(),
    TokenDistributionRule(),
    CallIslandsRule(),
]

__all__ = [
    "RULE_REGISTRY",
    "CyclomaticRule",
    "CognitiveRule",
    "CombinatorialRule",
    "GodModuleRule",
    "EscapeHatchesRule",
    "DuplicationRule",
    "DependencyCyclesRule",
    "RigidityRule",
    "UselessnessRule",
    "SentinelsRule",
    "HiddenMutatorsRule",
    "OrphansRule",
    "ClassShapeRule",
    "TokenDistributionRule",
    "CallIslandsRule",
]
