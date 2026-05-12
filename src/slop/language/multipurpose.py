"""``MultiPurpose`` — named diamond marker for multi-paradigm grammars.

A grammar that emits BOTH class-bound methods AND free functions
inherits from ``MultiPurpose``. The class itself has no method body;
it exists so kernels can write ``isinstance(g, MultiPurpose)`` instead
of the longer conjunction ``isinstance(g, ObjectOriented) and
isinstance(g, Procedural)``.

Both ``functions()`` and ``methods()`` are inherited (defaults to
``cls.callable()`` from the paradigm bases). Concrete grammars where
tree-sitter syntactically distinguishes function-vs-method nodes
override the relevant method.
"""
from __future__ import annotations

from abc import ABC

from .objectoriented import ObjectOriented
from .procedural import Procedural


class MultiPurpose(ObjectOriented, Procedural, ABC):
    """Named diamond — multi-paradigm marker. See module docstring."""
