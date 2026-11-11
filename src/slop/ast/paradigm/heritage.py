"""The classes a heritage clause names (``extends``, ``implements``, ``: Base``, ``<: Shape``).

A base entry names a class however it is written: a generic by its head (``List<T>``,
``Store[int]``, ``Box{Int}`` are ``List``, ``Store``, ``Box``) and a qualified name by its last
segment (``ns.Q``, ``Mod::D``, ``pkg.mod.Base`` are ``Q``, ``D``, ``Base``). The node types below
are the union across grammars; tree-sitter grammars do not reuse these names for anything else."""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any

#: a name as written
_NAMES = frozenset({"identifier", "type_identifier", "constant", "property_identifier"})
#: a generic or subscripted type, whose first named child is the class
_GENERICS = frozenset({"generic_type", "generic_name", "template_type", "subscript", "parametrized_type_expression"})
#: a qualified name, whose last named child is the class
_QUALIFIED = frozenset({"scoped_type_identifier", "nested_type_identifier", "qualified_name", "qualified_identifier",
                        "member_expression", "attribute", "scope_resolution", "field_expression"})


def type_name(node: Any, content: bytes) -> str | None:
    """The class a base entry names, or None when it is an expression (``mixin(B)``)."""
    while node.type in _GENERICS or node.type in _QUALIFIED:
        named = node.named_children
        if not named:
            return None
        node = named[0] if node.type in _GENERICS else named[-1]
    if node.type not in _NAMES:
        return None
    return content[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def heritage(node: Any, content: bytes, clauses: Iterable[str]) -> list[str]:
    """The classes named in ``node``'s heritage clauses: its children whose type is in
    ``clauses``, descending into nested clauses (a ``type_list`` inside ``implements``)."""
    clauses = frozenset(clauses)
    return [name for child in node.named_children if child.type in clauses
            for name in _entries(child, content, clauses)]


def _entries(clause: Any, content: bytes, clauses: frozenset[str]) -> list[str]:
    names: list[str] = []
    for entry in clause.named_children:
        if entry.type in clauses:
            names += _entries(entry, content, clauses)
            continue
        name = type_name(entry, content)
        if name is not None:
            names.append(name)
    return names
