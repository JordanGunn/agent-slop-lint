"""Span: a half-open byte range within a single source file.

slop's lowest layer: it depends on nothing, and both ``ast`` and ``lexicon`` key on it. The AST
proxy uses it for node identity; the scope model uses it for scope identity; the lexicon uses it
to record where each token occurs. It lives at the package root, not under ``ast/``, so that
``lexicon`` does not have to depend on ``ast`` to use it. ``slop.ast`` and
``slop.scope.identity`` re-export it.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, order=True)
class Span:
    """A half-open byte range within a single source file."""

    path: str
    start_byte: int
    end_byte: int
