"""Concrete rules. ``RULE_REGISTRY`` is the single flat list the dispatcher and
config consume. Each entry is a stateless ``Rule`` instance; its ``name`` and
``altitudes`` are class-level, and ``default_config`` ships its defaults.

Every rule here implements a measure with a published source (McCabe, Campbell,
Nejmeh, Martin, Lakos, Chidamber-Kemerer, Tornhill, Zipf) or a standard concept
(Type-2 clones, god module, unreferenced symbols). Rules whose measure and name were
slop's own invention were removed; see CHANGELOG.
"""
from __future__ import annotations

from ..rule import Rule
from .class_shape import ClassShapeRule
from .cognitive import CognitiveRule
from .combinatorial import CombinatorialRule
from .cyclomatic import CyclomaticRule
from .dependency_cycles import DependencyCyclesRule
from .duplication import DuplicationRule
from .god_module import GodModuleRule
from .hotspots import HotspotsRule
from .orphans import OrphansRule
from .rigidity import RigidityRule
from .token_distribution import TokenDistributionRule
from .uselessness import UselessnessRule

RULE_REGISTRY: list[Rule] = [
    CyclomaticRule(),
    CognitiveRule(),
    CombinatorialRule(),
    GodModuleRule(),
    DuplicationRule(),
    DependencyCyclesRule(),
    RigidityRule(),
    UselessnessRule(),
    OrphansRule(),
    HotspotsRule(),
    ClassShapeRule(),
    TokenDistributionRule(),
]

__all__ = [
    "RULE_REGISTRY",
    "CyclomaticRule",
    "CognitiveRule",
    "CombinatorialRule",
    "GodModuleRule",
    "DuplicationRule",
    "DependencyCyclesRule",
    "RigidityRule",
    "UselessnessRule",
    "OrphansRule",
    "HotspotsRule",
    "ClassShapeRule",
    "TokenDistributionRule",
]
