"""Paradigm tier — the ``Grammar`` ABC plus the capability markers that gate
which typed accessors a carved Module/Package exposes.

    Grammar (ABC)                  -- tabular tree-sitter contract (base.py)
      Procedural(Grammar)          -- functions()
      ObjectOriented(Grammar)      -- classes() [abstract], methods(), inheritance
      MultiPurpose(OO, Procedural) -- both (diamond)
"""
from __future__ import annotations

from .base import Grammar, Paradigm
from .objectoriented import ObjectOriented
from .procedural import Procedural
from .multipurpose import MultiPurpose

__all__ = ["Grammar", "Paradigm", "Procedural", "ObjectOriented", "MultiPurpose"]
