"""Re-export shim — identity primitives moved to ``slop.identity`` (the low base).

``ComponentKind``/``CallableKind``/``ComponentId``/``Extent`` are the substrate's
identity value types; like ``Span`` they now live at the package root
(``slop.identity``) so the scope model, metric views, graphs, and linter can share
them without depending on each other. This module re-exports them — plus ``Span`` —
so existing ``from ..scope.identity import …`` sites are unchanged during the
scope-layer migration.
"""
from __future__ import annotations

from ..identity import CallableKind, ComponentId, ComponentKind, Extent
from ..span import Span

__all__ = ["ComponentKind", "CallableKind", "ComponentId", "Extent", "Span"]
