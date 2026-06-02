"""The component model — ownership spine for slop v3.

    Corpus -> Realm -> Package -> Module -> Class -> Callable

Public surface: the ABC tier (``Component``, ``AggregateContainer``,
``SymbolContainer``), the six concrete kinds, identity/extent value types, the
``scan_corpus`` entry point, and the ``Selection`` region-union. Metrics live in
``metrics/structural`` (consumed via ``Structure.over(region)``), not here.
"""
from __future__ import annotations

from .aggregate import Corpus, Realm, Package
from .base import AggregateContainer, Component, SymbolContainer
from .identity import CallableKind, ComponentId, ComponentKind, Extent, Span
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
]
