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
    """Member names assigned through the instance receiver inside ``methods``."""
    access, assigning = grammar.member_access(), grammar.assignment_nodes()
    if access is None or not assigning:
        return
    for method in methods:
        yield from _method_assignments(grammar, method, access, assigning)


def _method_assignments(grammar: Any, method: Any, access: Any, assigning: Any) -> Iterable[str]:
    """Member names one method assigns through the receiver it calls its own instance."""
    receiver = grammar.instance_receiver(method._node, method._content)
    if receiver is None:
        return
    for node in method._ast_node().walk(prune=frozenset({NodeKind.CLASS})):
        member = _assigned_member(node, access, assigning, receiver)
        if member is not None:
            yield member


def _assigned_member(node: Any, access: Any, assigning: Any, receiver: str) -> str | None:
    """The member name when ``node`` reads as ``receiver.member`` on the left of an
    assignment, else ``None``."""
    if not _assigns_through(node, access, assigning):
        return None
    target, member = node.field(access.receiver_field), node.field(access.member_field)
    if target is None or member is None or target.text != receiver:
        return None
    return member.text


def _assigns_through(node: Any, access: Any, assigning: Any) -> bool:
    """Whether ``node`` is a member access whose parent assignment assigns to it."""
    if node.type != access.node_type:
        return False
    parent = node.parent
    return parent is not None and parent.type in assigning and parent.field("left") == node
