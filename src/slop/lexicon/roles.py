"""Role — the provenance of a named unit entering the lexicon.

What an identifier *names*, expressed in the lexicon's own vocabulary. This is a
lexicon-owned enum on purpose: it is **not** ``component.ScopeKind``. Importing
that would couple the lexicon upward to the component model and break the rule that
``lexicon/`` is usable outside the linter. The bridge (in the component layer) maps
``ScopeKind`` + identifier position onto a ``Role`` as units cross the boundary;
nothing AST- or component-shaped enters here.

Role-tagging lets a consumer select by provenance without re-walking syntax.
``build_declared_lexicon`` emits ``PACKAGE``/``MODULE`` (filesystem names) and
``CLASS``/``CALLABLE``/``PARAMETER``/``PROPERTY``, each for what the name declares. A
reference to a builtin or a library is not the project's word, and a local variable is
implementation detail, so neither is emitted.
"""
from __future__ import annotations

from enum import Enum


class Role(Enum):
    """Provenance of a named unit in a :class:`~slop.lexicon.corpus.Lexicon`."""

    REALM = "realm"
    PACKAGE = "package"
    MODULE = "module"
    CLASS = "class"
    CALLABLE = "callable"
    PARAMETER = "parameter"
    PROPERTY = "property"
