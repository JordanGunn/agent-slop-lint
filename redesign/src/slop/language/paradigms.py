"""Paradigm markers — the capability tier between ``Grammar`` and concrete grammars.

Ported from the legacy ``procedural`` / ``objectoriented`` / ``multipurpose``
markers. The paradigm decides which typed accessors a carved Module/Package
exposes; ``classes()`` is abstract on ``ObjectOriented`` only (ISP), and
non-inheriting OO languages still work because ``extract_superclasses`` defaults
to ``[]``.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

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


class MultiPurpose(ObjectOriented, Procedural, ABC):
    """Diamond marker — a grammar emitting both classes and free functions."""

    PARADIGM: ClassVar[Paradigm] = Paradigm.MULTI_PURPOSE
