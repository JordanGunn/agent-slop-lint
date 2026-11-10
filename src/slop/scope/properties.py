"""The properties a class declares: its class-body fields and the members its methods assign.

A property is vocabulary chosen where it is declared, so it belongs in the declared-names
lexicon beside classes and callables. Two sources, both read from syntax:

- fields the class body declares itself (``class_fields``: a Python class-level assignment,
  a TypeScript field);
- members assigned through the instance receiver inside a method (``self.x = ...``,
  ``this.x = ...``), which is how most Python and JavaScript classes declare their state.
  Constructors are included: that is where it is usually first assigned.

Both come from grammar facts, so a grammar that does not say (Java, C#, Go ...) yields no
properties for its classes rather than a guess.
"""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from ..ast import NodeKind


def class_properties(node: Any, content: bytes, grammar: Any, methods: Iterable[Any]) -> tuple[str, ...]:
    """Property names in first-seen order, without duplicates or special names.

    ``node`` is the raw class node; ``methods`` are the class's callable components."""
    names: list[str] = list(grammar.class_fields(node, content))
    names.extend(_assigned_members(grammar, methods))
    seen: set[str] = set()
    out: list[str] = []
    for name in names:
        if name not in seen and not grammar.is_special_method(name):
            seen.add(name)
            out.append(name)
    return tuple(out)


def _assigned_members(grammar: Any, methods: Iterable[Any]) -> Iterable[str]:
    access, assigning = grammar.member_access(), grammar.assignment_nodes()
    if access is None or not assigning:
        return
    for method in methods:
        receiver = grammar.instance_receiver(method._node, method._content)
        if receiver is None:
            continue
        for node in method._ast_node().walk(prune=frozenset({NodeKind.CLASS})):
            if node.type != access.node_type:
                continue
            parent = node.parent
            if parent is None or parent.type not in assigning or parent.field("left") != node:
                continue
            target, member = node.field(access.receiver_field), node.field(access.member_field)
            if target is not None and member is not None and target.text == receiver:
                yield member.text
