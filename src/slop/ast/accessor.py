"""Accessors: methods that only read or write one of their instance's members.

A getter or setter is a method whose only statement, a docstring and comments aside, returns
one instance member or assigns a plain value to one. The test is syntactic, so it reads the
same in every language whose grammar declares how instance members are spelled
(``member_access``) and named (``instance_receiver``); for any other language nothing is an
accessor.
"""
from __future__ import annotations

from typing import Any

from .binding import SymbolKind

#: node types that are not statements of a body
_NOT_STATEMENTS = ("comment",)


def is_accessor(method: Any, content: bytes, grammar: Any, bindings: dict) -> bool:
    """Whether ``method`` (a callable's syntax node) is a getter or setter: its only statement
    (a docstring and comments aside) returns one of the instance's members (``return self.x``,
    Rust's tail ``self.x``, Java's bare ``return x``) or assigns a plain value to one
    (``self.x = value``). A one-line call through the receiver (``self.shutdown()``) or
    arithmetic on a member (``self.a + 1``) is not an accessor. ``bindings`` are the file's
    name bindings (``slop.ast.binding``), which tell a bare field name from a local."""
    spellings = grammar.member_access()
    receiver = grammar.instance_receiver(method, content) if spellings else None
    body = method.child_by_field_name("body")
    if receiver is None or body is None:
        return False
    statements = [c for c in body.named_children if not any(t in c.type for t in _NOT_STATEMENTS)]
    if len(statements) > 1 and _is_docstring(statements[0]):
        statements = statements[1:]
    if len(statements) != 1:
        return False
    statement = _unwrapped(statements[0])
    if statement.type.startswith("assignment"):
        value = _unwrapped(statement.child_by_field_name("right"))
        target = _unwrapped(statement.child_by_field_name("left"))
        return _is_member(target, spellings, receiver, bindings) and value.named_child_count == 0
    return _is_member(statement, spellings, receiver, bindings)


def _unwrapped(node: Any) -> Any:
    """``node`` without the wrappers around a single expression: ``return``, an expression
    statement, Go's one-element ``statement_list`` and ``expression_list``."""
    while node.named_child_count == 1 and any(w in node.type for w in ("return", "statement", "_list")):
        node = node.named_children[0]
    return node


def _is_member(node: Any, spellings: Any, receiver: str, bindings: dict) -> bool:
    """``node`` is the instance's member: ``receiver.member``, or a bare name bound to a field."""
    for access in spellings:
        if node.type == access.node_type:
            target = node.child_by_field_name(access.receiver_field)
            return target is not None and target.text.decode() == receiver
    binding = bindings.get(node.start_byte)
    return node.named_child_count == 0 and binding is not None and binding.kind is SymbolKind.FIELD


def _is_docstring(node: Any) -> bool:
    return node.type == "expression_statement" and node.named_child_count == 1 and node.named_children[0].type == "string"
