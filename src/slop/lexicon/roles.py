"""Role — the provenance of a named unit entering the lexicon.

What an identifier *names*, expressed in the lexicon's own vocabulary. This is a
lexicon-owned enum on purpose: it is **not** ``component.ScopeKind``. Importing
that would couple the lexicon upward to the component model and break the rule that
``lexicon/`` is usable outside the linter. The bridge (in the component layer) maps
``ScopeKind`` + identifier position onto a ``Role`` as units cross the boundary;
nothing AST- or component-shaped enters here.

Role-tagging is what lets later consumers select by provenance without re-walking
syntax: named-entity analysis wants ``CLASS``/``CALLABLE`` names, first-parameter
clustering wants ``PARAMETER``, scope-overlap wants ``BODY_REF``.

Emission status (kept honest with the consumer-driven build):

- ``build_lexicon`` (the occurrence stream) emits ``REALM``/``PACKAGE``/``MODULE``
  (filesystem-derived names) and ``BODY_REF`` (every identifier the AST walk yields — the
  undifferentiated occurrence bucket).
- ``build_declared_lexicon`` (the declared names) emits ``REALM``/``PACKAGE``/``MODULE``
  plus ``CLASS``/``CALLABLE``/``PARAMETER``, split out by what each name declares; it has
  no ``BODY_REF``, because a reference to a builtin or library is not chosen vocabulary.
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
    BODY_REF = "body_ref"
