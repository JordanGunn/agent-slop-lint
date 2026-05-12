"""Language paradigm hierarchy + concrete grammars.

Re-exports the four paradigm classes so callers can write
``from slop.language import Language, MultiPurpose`` without
caring about the module decomposition under the hood. Concrete
grammars live in the nested ``grammars/`` subpackage; ``Tree``
imports ``DEFAULT_GRAMMARS`` from there.

See ``docs/planning/language.md`` for the locked design.
"""
from __future__ import annotations

from .base import Language
from .multipurpose import MultiPurpose
from .objectoriented import ObjectOriented
from .procedural import Procedural

__all__ = [
    "Language",
    "ObjectOriented",
    "Procedural",
    "MultiPurpose",
]
