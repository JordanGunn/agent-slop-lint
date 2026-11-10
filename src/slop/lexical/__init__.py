"""slop.lexical — lexical analysis: observed identifier vocabulary against a canonical one.

Sits above ``slop.lexicon`` (the observed token-space) and ``slop.ontology`` (the
canonical vocabulary), and depends on neither's internals: :func:`coverage` takes a
``Lexicon`` and a ``Vocabulary``.
"""
from __future__ import annotations

from .coverage import Coverage, Observed, canonical_tokens, coverage

__all__ = ["Coverage", "Observed", "canonical_tokens", "coverage"]
