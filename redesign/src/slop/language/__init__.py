"""Grammar adapter layer — owned by ``Realm``.

The ported legacy ``slop.language`` paradigm hierarchy:

    Grammar (ABC)                  -- tabular tree-sitter contract (base.py)
      Procedural(Grammar)          -- functions()
      ObjectOriented(Grammar)      -- classes() [abstract here only], methods()
      MultiPurpose(OO, Procedural) -- both (diamond)

A ``Realm`` owns one ``Grammar``; the grammar's ``PARADIGM`` gates which typed
accessors the Realm's carved Modules/Packages expose. ``Grammar`` + ``Paradigm``
are re-exported here because the (untouched) component interfaces import them.
"""
from __future__ import annotations

from .base import Grammar, Paradigm
from .grammars import GRAMMARS_BY_ID, Python
from .paradigms import MultiPurpose, ObjectOriented, Procedural

__all__ = [
    "Grammar",
    "Paradigm",
    "Procedural",
    "ObjectOriented",
    "MultiPurpose",
    "Python",
    "GRAMMARS_BY_ID",
]
