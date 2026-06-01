"""``Procedural`` — grammars emitting free functions with no implicit receiver."""
from __future__ import annotations

from abc import ABC
from typing import ClassVar

from .base import Grammar, Paradigm


class Procedural(Grammar, ABC):
    """Grammar emitting free functions — callables with no implicit receiver."""

    PARADIGM: ClassVar[Paradigm] = Paradigm.PROCEDURAL

    @classmethod
    def functions(cls) -> frozenset[str]:
        """Node types defining free functions. Default: the full callable set."""
        return cls.callable()
