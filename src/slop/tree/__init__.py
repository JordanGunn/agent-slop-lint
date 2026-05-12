"""``slop.tree`` — Tree (parsed source forest) + records.

``Tree`` is the new name for what was ``Codebase`` in earlier design
rounds — an AST-tree-walker that scans a corpus, parses each file via
its grammar, and produces ``Structure`` and ``Lexicon`` views.

The ``Tree`` class is NOT re-exported eagerly here because
``slop.structure`` and ``slop.lexicon`` need to import from
``slop.tree.records`` without triggering the Tree class's heavy
import chain (which would re-enter this package and deadlock).

Callers do ``from slop.tree.tree import Tree`` directly.

See ``docs/planning/codebase.md`` for the locked design.
"""
from __future__ import annotations

from .records import (
    Callable,
    CallableKind,
    Occurrence,
    Parameter,
    ParseResult,
    Scope,
    ScopeKind,
)

__all__ = [
    "Scope",
    "Callable",
    "Occurrence",
    "Parameter",
    "ParseResult",
    "ScopeKind",
    "CallableKind",
]
