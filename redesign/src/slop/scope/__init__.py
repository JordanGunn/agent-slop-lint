"""The component model — ownership spine for slop v3.

    Corpus -> Realm -> Package -> Module -> Class -> Callable

Public surface: the ABC tier (``Scope``, ``AggregateContainer``,
``SymbolContainer``), the six concrete kinds, identity/extent value types, the
``scan_corpus`` entry point, and the ``Selection`` region-union. Metrics live in
``metrics/structural`` (consumed via ``Structure.over(region)``), not here.
"""
from __future__ import annotations

from .aggregate import Corpus, Realm, Package
from .base import AggregateContainer, Scope, SymbolContainer
from .identity import CallableKind, ScopeId, ScopeKind, Extent, Span
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
    "Scope",
    "AggregateContainer",
    "SymbolContainer",
    "Corpus",
    "Realm",
    "Package",
    "Module",
    "Class",
    "Callable",
    # identity
    "ScopeId",
    "ScopeKind",
    "CallableKind",
    "Extent",
    "Span",
    # projection
    "Lexicon",
]
