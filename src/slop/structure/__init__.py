"""``slop.structure`` — Structure view + structural rules.

The Structure view exposes scopes, callables, parent/child
relationships, and per-callable structural metrics (cyclomatic,
cognitive, npath, halstead, etc.). Structural rules consume this view.
"""
from __future__ import annotations

from .view import Structure

__all__ = ["Structure"]
