"""Span — a half-open byte range within a single source file.

The atomic source-location primitive, and slop's lowest layer: it depends on
nothing. It lives at the package root — not under ``ast/`` — because more than one
bottom-layer subsystem keys on it. The AST proxy uses it for node identity; the
component model uses it for component identity; the lexicon uses it both to record
token dispersion and as the join key when a rule correlates a lexical signal with a
structural one. ``ast`` and ``lexicon`` are peers that both depend on ``span``;
neither depends on the other. (``Span`` was never an AST type — keeping it under
``ast/`` would force ``lexicon -> ast`` the moment lexicon needed it.)

``slop.ast`` and ``slop.component.identity`` both re-export ``Span``, so existing
``from ..ast import Span`` / ``from ..component.identity import Span`` sites are
unchanged.

tree-sitter node identity is not stable across accesses, so a node's durable
identity is its span, never ``id(node)``.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, order=True)
class Span:
    """A half-open byte range within a single source file."""

    path: str
    start_byte: int
    end_byte: int
