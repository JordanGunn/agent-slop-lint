"""Paradigm markers — the capability tier between ``Grammar`` and concrete grammars.

Ported from the legacy ``procedural`` / ``objectoriented`` / ``multipurpose``
markers. The paradigm decides which capabilities a carved Module/Package exposes.
Class/inheritance accessors (``classes``, ``is_abstract_scope``,
``extract_superclasses``, ``reparent_callable``) live on ``ObjectOriented`` — they
are meaningless for a procedural language and so must not sit on the base
``Grammar``. ``classes()`` is abstract (every OO grammar must declare it); the
inheritance accessors carry not-applicable defaults so a non-inheriting OO
language (e.g. Go structs) still works without overriding them.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar

from .base import Grammar, Paradigm


class Procedural(Grammar, ABC):
    """Grammar emitting free functions — callables with no implicit receiver."""

    PARADIGM: ClassVar[Paradigm] = Paradigm.PROCEDURAL

    @classmethod
    def functions(cls) -> frozenset[str]:
        """Node types defining free functions. Default: the full callable set."""
        return cls.callable()


class ObjectOriented(Grammar, ABC):
    """Grammar with named scopes containing methods that have implicit receivers."""

    PARADIGM: ClassVar[Paradigm] = Paradigm.OBJECT_ORIENTED

    @classmethod
    @abstractmethod
    def classes(cls) -> frozenset[str]:
        """Node types defining class-like scopes."""

    @classmethod
    def methods(cls) -> frozenset[str]:
        """Node types defining methods. Default: the full callable set."""
        return cls.callable()

    @classmethod
    def is_abstract_scope(cls, node: Any, content: bytes) -> bool | None:
        """Classify a class-like scope abstract/concrete/neither (None). Default None."""
        del node, content
        return None

    @classmethod
    def extract_superclasses(cls, node: Any, content: bytes) -> list[str]:
        """Base-class / interface names declared on a class node. Default empty."""
        del node, content
        return []

    @classmethod
    def reparent_callable(cls, node: Any, content: bytes) -> str | None:
        """Simple name of the type a callable structurally belongs to, when the
        grammar emits it outside that type's body (Go receiver methods, Rust impl
        functions). The carver attaches it to the matching Class by construction —
        replacing the legacy ``post_scan_adjust`` record-rewrite. Default None."""
        del node, content
        return None


class MultiPurpose(ObjectOriented, Procedural, ABC):
    """Diamond marker — a grammar emitting both classes and free functions."""

    PARADIGM: ClassVar[Paradigm] = Paradigm.MULTI_PURPOSE
