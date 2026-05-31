"""Capability interfaces — paradigm-specific component surface.

DO NOT grow a parallel capability vocabulary here. The legacy
``slop.language`` hierarchy already models paradigm capability correctly and is
directly portable as the ``Realm``'s grammar adapter:

    Language (ABC)                 -- tabular tree-sitter contract (~40 classmethods)
      Procedural(Language)         -- functions()                  (free functions)
      ObjectOriented(Language)     -- classes() [abstract here only], methods()
      MultiPurpose(OO, Procedural) -- both (diamond marker)

That hierarchy answers, per language, *which symbol kinds exist*. In the
component model the ``Realm`` owns a paradigm-typed grammar adapter, and the
adapter's paradigm decides which typed accessors a carved Module/Package
exposes: a Procedural realm's Modules expose ``functions()``/``constants()``
and no ``classes()``; an ObjectOriented realm's the reverse; a MultiPurpose
library's both.

So this module stays empty of invented protocols. The single capability below
is a provisional component-side marker pending the adapter port (which will make
it derive from the grammar paradigm rather than be declared independently).
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from .symbol import Class


@runtime_checkable
class HasClasses(Protocol):
    """A container whose language emits class-like types (mirrors the legacy
    ``ObjectOriented`` paradigm marker). Provisional — to be reconciled with the
    ported grammar-paradigm hierarchy, which is the real source of truth.
    """

    def classes(self) -> Sequence["Class"]:
        ...
