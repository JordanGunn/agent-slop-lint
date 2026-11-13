"""Reading tree-sitter syntax nodes: the helpers several grammars share."""
from __future__ import annotations

from typing import Any

IDENTIFIER = "identifier"


def node_text(node: Any, content: bytes) -> str:
    """The source text spanned by ``node``."""
    return content[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def first_identifier(node: Any, identifier_types: frozenset[str] = frozenset({IDENTIFIER})) -> Any:
    """DFS for the first identifier-typed descendant (the name buried in a C/C++
    declarator: ``char *name`` → ``pointer_declarator`` → ``identifier``)."""
    if node is None:
        return None
    stack = [node]
    while stack:
        n = stack.pop(0)
        if n.type in identifier_types:
            return n
        stack.extend(n.children)
    return None


def child_of_type(node: Any, type_name: str) -> Any:
    if node is None:
        return None
    for child in node.children:
        if child.type == type_name:
            return child
    return None


def has_keyword(node: Any, content: bytes, child_type: str, keyword: str) -> bool:
    """Whether a direct child of ``node`` typed ``child_type`` reads ``keyword`` (C#'s ``modifier``
    or C++'s ``storage_class_specifier`` reading ``static``)."""
    return any(c.type == child_type and content[c.start_byte:c.end_byte].decode("utf-8", errors="replace") == keyword
               for c in node.children)


def type_specifier_name(node: Any, content: bytes) -> str:
    """A C/C++ struct/union/enum/class specifier's tag, else the name of the ``typedef``
    that wraps an anonymous one (``typedef struct { ... } Point;`` is ``Point``)."""
    name = node.child_by_field_name("name")
    if name is None and node.parent is not None and node.parent.type == "type_definition":
        name = node.parent.child_by_field_name("declarator")
    if name is None or name.type not in ("type_identifier", IDENTIFIER):
        return "<anonymous>"
    return content[name.start_byte:name.end_byte].decode("utf-8", errors="replace")
