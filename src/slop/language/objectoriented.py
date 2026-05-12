"""``ObjectOriented`` — paradigm marker for grammars with named scopes
containing methods with implicit receivers.

Covers Java, Python, C++, Ruby, Go (struct + receiver methods), Rust
(impl blocks), C#, TypeScript, JavaScript. All four pillars of OOP
need not apply (Rust lacks inheritance); the criterion is the
receiver-binding semantic, not the full OOP suite.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from .base import Language


class ObjectOriented(Language, ABC):
    """Marker for grammars whose syntax emits named scopes containing
    methods with implicit receivers."""

    @classmethod
    @abstractmethod
    def classes(cls) -> frozenset[str]:
        """Tree-sitter node types that define class-like scopes."""

    @classmethod
    def methods(cls) -> frozenset[str]:
        """Tree-sitter node types that define methods.

        Default: ``cls.callable()`` — the full callable set. Override
        on grammars where tree-sitter splits free-function and method
        node types syntactically (e.g. JS ``method_definition`` vs
        ``function_declaration``; Go ``method_declaration`` vs
        ``function_declaration``), OR where a callable node type can
        appear only as a free function (e.g. Python's ``lambda``).
        """
        return cls.callable()
