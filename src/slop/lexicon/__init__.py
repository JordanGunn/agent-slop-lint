"""``slop.lexicon`` — Lexicon view + lexical rules.

The Lexicon view exposes the identifier-token bag plus per-callable
lexical computations (first-parameter clustering, body signatures,
modal-token overlap). Lexical rules consume this view.
"""
from __future__ import annotations

from .view import Lexicon

__all__ = ["Lexicon"]
