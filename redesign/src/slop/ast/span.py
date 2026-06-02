"""Span — a half-open byte range within a single source file.

The atomic source-location primitive. It lives in ``ast/`` — the lowest layer —
because both the AST proxy and the component model key identity on it, and the
component layer already depends on ``ast`` (``Grammar``/``Paradigm``). Keeping
``Span`` here is what makes the ``component -> ast`` edge one-directional;
``component.identity`` re-exports it so existing
``from ..component.identity import Span`` sites are unchanged.

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
