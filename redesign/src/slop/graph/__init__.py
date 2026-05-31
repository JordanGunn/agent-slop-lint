"""Derived graphs — downstream projections over a built component hierarchy.

The component hierarchy answers "what owns what"; the graphs answer "what
depends on what" (``DependencyGraph``) and "what calls what" (``CallGraph``,
deferred). They are built after the ownership spine is solid and piggyback on
it — see DESIGN.md.
"""
from __future__ import annotations

from .dependency import DependencyEdge, DependencyGraph

__all__ = ["DependencyGraph", "DependencyEdge"]
