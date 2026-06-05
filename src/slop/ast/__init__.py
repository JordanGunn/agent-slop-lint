"""Grammar adapter layer — owned by ``Realm``.

The paradigm hierarchy lives in ``paradigm/``:

    Grammar (ABC)                  -- tabular tree-sitter contract (paradigm/base.py)
      Procedural(Grammar)          -- functions()
      ObjectOriented(Grammar)      -- classes() [abstract here only], methods()
      MultiPurpose(OO, Procedural) -- both (diamond)

A ``Realm`` owns one ``Grammar``; the grammar's ``PARADIGM`` gates which typed
accessors the Realm's carved Modules/Packages expose. ``Grammar`` + ``Paradigm``
are re-exported here because the component interfaces import them.

``slop.ast`` is the home of slop's AST concept: a language-agnostic, pythonic
*proxy over tree-sitter* (``AST`` + ``Node``, ``tree.py``) that owns all syntax
navigation and isolates raw tree-sitter nodes to this package. ``NodeKind`` (the
neutral node vocabulary) lives here; ``Span`` (the source-location primitive) lives
one layer lower in ``slop.span`` — a shared base ``ast`` and ``lexicon`` both depend
on — and is re-exported here for unchanged ``from ..ast import Span`` sites. Nothing
above ``ast/`` touches a raw node.
"""
from __future__ import annotations

from ..span import Span
from .grammar import GRAMMARS_BY_ID, Python
from .nodes import NodeKind
from .paradigm import Grammar, MultiPurpose, ObjectOriented, Paradigm, Procedural
from .tree import AST, Node

__all__ = [
    "Grammar",
    "Paradigm",
    "Procedural",
    "ObjectOriented",
    "MultiPurpose",
    "Python",
    "GRAMMARS_BY_ID",
    "AST",
    "Node",
    "NodeKind",
    "Span",
]
