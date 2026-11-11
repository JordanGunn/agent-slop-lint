"""Descendant iteration over anything that has ``children()``: a scope or a ``Selection``.

The metric views and rules read this surface (``_iter_callables``, ``_iter_classes``,
``_iter_modules``) without importing the concrete scope classes.
"""
from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from .identity import ScopeKind


class Descendants:
    def _iter_kind(self, kind: ScopeKind) -> Iterator[Any]:
        for child in self.children():
            if child.KIND == kind:
                yield child
            yield from child._iter_kind(kind)

    def _children_of(self, kind: ScopeKind) -> tuple[Any, ...]:
        return tuple(c for c in self.children() if c.KIND == kind)

    def _iter_callables(self) -> Iterator[Any]:
        return self._iter_kind(ScopeKind.CALLABLE)

    def _iter_classes(self) -> Iterator[Any]:
        return self._iter_kind(ScopeKind.CLASS)

    def _iter_modules(self) -> Iterator[Any]:
        return self._iter_kind(ScopeKind.MODULE)
