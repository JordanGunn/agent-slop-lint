"""``Procedural`` — paradigm marker for grammars emitting free functions.

Covers C, Julia, and the procedural side of multi-paradigm grammars.
"""
from __future__ import annotations

from abc import ABC

from .base import Language


class Procedural(Language, ABC):
    """Marker for grammars whose syntax emits free functions —
    callables with no implicit receiver and no enclosing class scope.

    ``functions()`` defaults to ``cls.callable()`` — in pure-procedural
    languages all callables are free functions. MultiPurpose grammars
    where tree-sitter explicitly distinguishes free-function and method
    node types (Go, JS, TS) override ``functions()`` to return the
    function-only subset.
    """

    @classmethod
    def functions(cls) -> frozenset[str]:
        """Tree-sitter node types that define free functions.

        Default: ``cls.callable()`` — the full callable set. Override
        on grammars where tree-sitter splits free-function and method
        node types syntactically.
        """
        return cls.callable()
