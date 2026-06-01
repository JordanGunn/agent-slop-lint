"""Grammar adapter layer — owned by ``Realm``.

The paradigm hierarchy lives in ``paradigm/``:

    Grammar (ABC)                  -- tabular tree-sitter contract (paradigm/base.py)
      Procedural(Grammar)          -- functions()
      ObjectOriented(Grammar)      -- classes() [abstract here only], methods()
      MultiPurpose(OO, Procedural) -- both (diamond)

A ``Realm`` owns one ``Grammar``; the grammar's ``PARADIGM`` gates which typed
accessors the Realm's carved Modules/Packages expose. ``Grammar`` + ``Paradigm``
are re-exported here because the component interfaces import them. ``slop.ast``
is the home of slop's AST concept — the persistent AST projection (currently
``model/ast.py``) will move under here.
"""
from __future__ import annotations

from .grammar import GRAMMARS_BY_ID, Python
from .paradigm import Grammar, MultiPurpose, ObjectOriented, Paradigm, Procedural

__all__ = [
    "Grammar",
    "Paradigm",
    "Procedural",
    "ObjectOriented",
    "MultiPurpose",
    "Python",
    "GRAMMARS_BY_ID",
]
