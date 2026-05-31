"""Grammar adapter layer — owned by ``Realm``.

This package is where the legacy ``slop.language`` hierarchy ports to:

    Language (ABC)                 -- tabular tree-sitter contract
      Procedural(Language)         -- functions()
      ObjectOriented(Language)     -- classes() [abstract here only], methods()
      MultiPurpose(OO, Procedural) -- both

It is the directly-portable inventory item that answers, per language, *which
symbol kinds exist* and how to carve them. A ``Realm`` owns exactly one
``Grammar``; the grammar's ``paradigm`` gates which typed accessors the Realm's
carved Modules/Packages expose.

Until the port, ``Grammar`` and ``Paradigm`` below mark the seam and the
ownership edge so nothing references a grammar ad-hoc.

Design note (avoid the legacy's over-control): the legacy ``Language`` exported
~20 control-flow node-type knobs to steer one central complexity walker, and a
``post_scan_adjust`` hook to rewrite mis-parented records after a generic walk.
The ported design should prefer carving that parents correctly by construction
and a grammar that owns (or co-owns) its own walks, rather than re-exporting that
control surface.
"""
from __future__ import annotations

from abc import ABC
from enum import Enum
from typing import ClassVar


class Paradigm(Enum):
    """The capability tier of a grammar — decides which typed accessors a
    carved Module/Package exposes."""

    PROCEDURAL = "procedural"          # free functions, no classes (C, Julia)
    OBJECT_ORIENTED = "object_oriented"  # classes + methods, no free functions (Java, C#)
    MULTI_PURPOSE = "multi_purpose"    # both (Python, Go, Rust, C++, Ruby, TS, JS)


class Grammar(ABC):
    """Placeholder for the ported grammar contract a ``Realm`` owns.

    Concrete grammars will declare ``id`` (the language identifier / tree-sitter
    package suffix) and ``PARADIGM``; the full tabular tree-sitter surface ports
    from legacy ``slop.language``.
    """

    id: ClassVar[str]
    PARADIGM: ClassVar[Paradigm]
