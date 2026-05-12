"""C grammar — procedural; no classes.

Overrides ``extract_name`` to walk the declarator chain
(``function_declarator → identifier``), which tree-sitter-c uses
instead of a ``name`` field.
"""
from __future__ import annotations

from typing import Any, ClassVar

from ..ast import Node
from ..procedural import Procedural


class C(Procedural):
    id: ClassVar[str] = "c"

    @classmethod
    def callable(cls) -> frozenset[str]:
        return frozenset({Node.FUNCTION_DEFINITION})

    @classmethod
    def decision_nodes(cls) -> frozenset[str]:
        return frozenset({
            Node.IF_STATEMENT,
            Node.FOR_STATEMENT, Node.WHILE_STATEMENT, Node.DO_STATEMENT,
            Node.CASE_STATEMENT,            # both `case X:` and `default:`
            Node.CONDITIONAL_EXPRESSION,    # ternary `?:`
        })

    @classmethod
    def nesting_nodes(cls) -> frozenset[str]:
        return frozenset({
            Node.IF_STATEMENT,
            Node.FOR_STATEMENT, Node.WHILE_STATEMENT, Node.DO_STATEMENT,
            Node.SWITCH_STATEMENT,          # container for case_statement
            Node.CONDITIONAL_EXPRESSION,
        })

    @classmethod
    def compensating_decisions(cls) -> frozenset[str]:
        return frozenset({Node.CASE_STATEMENT})

    @classmethod
    def boolean_op_node(cls) -> str | None:
        return Node.BINARY_EXPRESSION

    @classmethod
    def boolean_op_operators(cls) -> frozenset[str] | None:
        return frozenset({"&&", "||"})

    @classmethod
    def extract_name(cls, node: Any, content: bytes) -> str:
        """Walk the C declarator chain to the identifier."""
        if node.type != Node.FUNCTION_DEFINITION:
            return super().extract_name(node, content)
        declarator = node.child_by_field_name("declarator")
        for _ in range(6):
            if declarator is None:
                return "<anonymous>"
            if declarator.type == Node.FUNCTION_DECLARATOR:
                inner = declarator.child_by_field_name("declarator")
                if inner is not None and inner.type == Node.IDENTIFIER:
                    return content[inner.start_byte:inner.end_byte].decode(
                        "utf-8", errors="replace",
                    )
                return "<anonymous>"
            if declarator.type in (Node.POINTER_DECLARATOR, Node.PARENTHESIZED_DECLARATOR):
                declarator = declarator.child_by_field_name("declarator")
                continue
            break
        return "<anonymous>"
