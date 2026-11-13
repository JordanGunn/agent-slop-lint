"""Role: what kind of declaration a name entering the lexicon names.

The lexicon's own enum, not ``slop.scope.identity.ScopeKind``: importing that would couple the
lexicon to the scope model and break the rule that ``lexicon/`` is usable outside the linter.
``slop.scope.lexicon`` maps each scope kind and identifier position onto a ``Role`` as names
enter the lexicon.

Role-tagging lets a consumer select by provenance without re-walking syntax.
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
