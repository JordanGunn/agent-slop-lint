"""Graphs over the scope tree.

``DependencyGraph``: which modules import which, with each module's afferent and efferent
coupling and the import cycles. Carving builds it and keeps it on the analysis context.
"""
from __future__ import annotations

from .dependency import DependencyEdge, DependencyGraph

__all__ = ["DependencyGraph", "DependencyEdge"]
