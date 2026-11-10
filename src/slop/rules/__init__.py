"""Concrete rules. ``RULE_REGISTRY`` is the single flat list the dispatcher and config
consume. Each entry is a stateless ``Rule`` instance; its ``name``, ``description`` and
``altitudes`` are class-level, and ``default_config`` ships its defaults.

Every rule checks one measure that has a published source (McCabe, Campbell, Nejmeh,
Halstead, Martin, Lakos, Chidamber and Kemerer, Hitz and Montazeri) or a standard concept (Type-2
clones, module size, magic numbers) against a limit. A rule is a threshold on a measure and nothing more.
"""
from __future__ import annotations

from ..rule import Rule
from .class_design import ChildrenRule, CohesionRule, CouplingRule, InheritanceDepthRule
from .cognitive import CognitiveRule
from .combinatorial import CombinatorialRule
from .cyclomatic import CyclomaticRule
from .dependency_cycles import DependencyCyclesRule
from .duplication import DuplicationRule
from .duplicate_string import DuplicateStringRule
from .god_module import GodModuleRule
from .halstead import HalsteadVolumeRule
from .magic_float import MagicFloatRule
from .rigidity import RigidityRule
from .uselessness import UselessnessRule

RULE_REGISTRY: list[Rule] = [
    CyclomaticRule(),
    CognitiveRule(),
    CombinatorialRule(),
    HalsteadVolumeRule(),
    MagicFloatRule(),
    DuplicateStringRule(),
    GodModuleRule(),
    DuplicationRule(),
    DependencyCyclesRule(),
    RigidityRule(),
    UselessnessRule(),
    CouplingRule(),
    InheritanceDepthRule(),
    ChildrenRule(),
    CohesionRule(),
]

__all__ = [
    "RULE_REGISTRY",
    "ChildrenRule",
    "CognitiveRule",
    "CohesionRule",
    "CombinatorialRule",
    "CouplingRule",
    "CyclomaticRule",
    "DependencyCyclesRule",
    "DuplicateStringRule",
    "DuplicationRule",
    "GodModuleRule",
    "HalsteadVolumeRule",
    "InheritanceDepthRule",
    "MagicFloatRule",
    "RigidityRule",
    "UselessnessRule",
]
