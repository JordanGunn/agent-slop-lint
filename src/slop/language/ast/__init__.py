"""``slop.language.ast`` — tree-sitter node-type registry.

Single source of truth for the tree-sitter node-type strings consumed
by grammar classmethods and view computations. Each grammar references
these enum members instead of inline string literals, which prevents
typos and gives IDE autocomplete + cross-grammar grep visibility.

Membership in ``Node`` does NOT imply universality — many of these
node types are language-specific (Rust's ``if_expression`` vs Python's
``if_statement`` vs Ruby's ``if``). The enum is a flat registry of
every node-type string that any v2 grammar mentions; per-grammar
selection lives on the grammar classes themselves.
"""
from __future__ import annotations

from .nodes import Node

__all__ = ["Node"]
