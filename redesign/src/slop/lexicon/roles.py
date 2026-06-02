"""Role — the provenance of a named unit entering the lexicon.

What an identifier *names*, expressed in the lexicon's own vocabulary. This is a
lexicon-owned enum on purpose: it is **not** ``component.ComponentKind``. Importing
that would couple the lexicon upward to the component model and break the rule that
``lexicon/`` is usable outside the linter. The bridge (in the component layer) maps
``ComponentKind`` + identifier position onto a ``Role`` as units cross the boundary;
nothing AST- or component-shaped enters here.

Role-tagging is what lets later consumers select by provenance without re-walking
syntax: named-entity analysis wants ``CLASS``/``CALLABLE`` names, first-parameter
clustering wants ``PARAMETER``, scope-overlap wants ``BODY_REF``.

Emission status (kept honest with the consumer-driven build):

- Emitted today: ``REALM``/``PACKAGE``/``MODULE`` (filesystem-derived names) and
  ``BODY_REF`` (every identifier the AST walk yields — the undifferentiated
  occurrence bucket).
- Reserved: ``CLASS``/``CALLABLE``/``PARAMETER``. The vocabulary they describe is
  fixed here so the interface is stable, but the bridge does not yet split them out
  of ``BODY_REF`` — that finer partition is wired when the first rule that
  distinguishes them lands and the bridge gains name/parameter span information.
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
