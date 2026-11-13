"""slop.ast: parsing source with tree-sitter, and reading the trees.

``parse`` loads a language's tree-sitter grammar and parses files; ``tree`` wraps the result
as ``AST`` and ``Node``, a language-agnostic proxy that owns all navigation, so nothing outside
this package touches a raw tree-sitter node. ``NodeKind`` names the constructs the proxy
classifies. ``grammar`` holds one ``Grammar`` per language (its interface is
``grammar/interface.py``); ``binding`` resolves names to what they refer to; ``accessor`` tells
getters and setters apart.
"""
from __future__ import annotations

from ..span import Span
from .grammar import GRAMMARS_BY_ID, Python
from .grammar.interface import Grammar
from .nodes import NodeKind
from .tree import AST, Node

__all__ = [
    "Grammar",
    "Python",
    "GRAMMARS_BY_ID",
    "AST",
    "Node",
    "NodeKind",
    "Span",
]
