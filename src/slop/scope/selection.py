"""Selection — a union of regions, addressable as a single region.

The granular-scoping primitive: a *set* of scopes is itself a region to the view
layer, so a view constructed over it sees the union. ``Structure.over(selection)`` and
the lexicon bridge consume it through the same duck-typed surface a single scope
exposes (``KIND``/``_node``/``children``/``_iter_callables``/``_iter_classes``), so no
view needs to know it is handling a composite.

What composes cleanly over a union:

- **Lexicon** — the combined vocabulary (the kernel just sees more tokens).
- **Additive structural metrics** — ``cyclomatic``/``cognitive``/``combinatorial``/
  ``volume``/``sloc`` sum over the union's callables.

What does *not*: altitude-bound metrics (CK at a Class, Martin at a Package) are
undefined over an arbitrary union and are deliberately not offered — a ``Selection``
exposes no ``methods()``/``modules()``, so ``Structure.over(selection).ck()`` raises
rather than returning a false number.
"""
from __future__ import annotations

from typing import Any, Iterable

from .descendants import Descendants


class Selection(Descendants):
    """A composite region over a set of scopes. ``Structure.over`` / the lexicon
    bridge treat it like any region; it owns no AST node and aggregates its members."""

    #: A composite is not a single kind — sentinels keep it out of the leaf
    #: (``== CALLABLE``) and fs-name (``in _FS_NAMED``) tests the views run.
    KIND = None
    _node = None

    def __init__(self, regions: Iterable[Any]) -> None:
        self._regions = tuple(regions)

    def children(self) -> tuple[Any, ...]:
        return self._regions

