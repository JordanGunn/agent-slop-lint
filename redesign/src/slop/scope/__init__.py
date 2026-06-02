"""The component model — ownership spine for slop v3.

    Corpus -> Realm -> Package -> Module -> Class -> Callable

Public surface: the ABC tier (``Component``, ``AggregateContainer``,
``SymbolContainer``), the six concrete kinds, identity/extent value types, the
capability protocols, and the metric value records. Interfaces only — no
implementation until the spine is validated against the hard rules.
"""
from __future__ import annotations

from .aggregate import Corpus, Realm, Package
from .base import AggregateContainer, Component, SymbolContainer
from .identity import CallableKind, ComponentId, ComponentKind, Extent, Span
from .metrics import (
    CallIsland,
    CKMetrics,
    CloneCluster,
    DependencyCycle,
    HalsteadProfile,
    Hotspot,
    ImportDecl,
    MagicLiteral,
    Orphan,
    PackageMetrics,
    ParameterMutation,
    RedundancyPair,
    SentinelParameter,
)
from .carve import scan_corpus
from .projection import Lexicon
from .selection import Selection
from .symbol import Callable, Class, Module

__all__ = [
    # entry point
    "scan_corpus",
    # granular scoping
    "Selection",
    # spine
    "Component",
    "AggregateContainer",
    "SymbolContainer",
    "Corpus",
    "Realm",
    "Package",
    "Module",
    "Class",
    "Callable",
    # identity
    "ComponentId",
    "ComponentKind",
    "CallableKind",
    "Extent",
    "Span",
    # projection
    "Lexicon",
    # metric records
    "HalsteadProfile",
    "CKMetrics",
    "PackageMetrics",
    "MagicLiteral",
    "ParameterMutation",
    "SentinelParameter",
    "RedundancyPair",
    "CloneCluster",
    "CallIsland",
    "Orphan",
    "Hotspot",
    "DependencyCycle",
    "ImportDecl",
]
