"""slop.ontology — the canonical-vocabulary layer.

The boundary (:class:`Vocabulary`, :class:`Term`) is what the rest of slop may depend
on. :class:`OntologyIR` is the one concrete reader, for Open Ontology JSON IR.
:func:`compare` sets the names observed in code against a vocabulary.
"""
from __future__ import annotations

from .compare import Comparison, compare
from .interface import Term, TermKind, Vocabulary, normalize
from .ir import OntologyError, OntologyIR

__all__ = [
    "Comparison",
    "OntologyError",
    "OntologyIR",
    "Term",
    "TermKind",
    "Vocabulary",
    "compare",
    "normalize",
]
