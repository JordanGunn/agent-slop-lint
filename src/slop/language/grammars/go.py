"""Go grammar — struct + receiver-bound methods + free functions.

Tree-sitter-go syntactically distinguishes ``function_declaration``
(free) from ``method_declaration`` (receiver). Both are callables;
``functions()`` and ``methods()`` return distinct subsets.
"""
from __future__ import annotations

from typing import ClassVar

from ..ast import Node
from ..multipurpose import MultiPurpose


class Go(MultiPurpose):
    id: ClassVar[str] = "go"

    @classmethod
    def callable(cls) -> frozenset[str]:
        return frozenset({
            Node.FUNCTION_DECLARATION, Node.METHOD_DECLARATION, Node.FUNC_LITERAL,
        })

    @classmethod
    def classes(cls) -> frozenset[str]:
        # Go doesn't have classes; struct + interface are the closest.
        return frozenset({Node.TYPE_DECLARATION})

    @classmethod
    def identifiers(cls) -> frozenset[str]:
        return frozenset({Node.IDENTIFIER, Node.FIELD_IDENTIFIER, Node.TYPE_IDENTIFIER})

    @classmethod
    def functions(cls) -> frozenset[str]:
        return frozenset({Node.FUNCTION_DECLARATION, Node.FUNC_LITERAL})

    @classmethod
    def methods(cls) -> frozenset[str]:
        return frozenset({Node.METHOD_DECLARATION})

    @classmethod
    def decision_nodes(cls) -> frozenset[str]:
        return frozenset({
            Node.IF_STATEMENT,
            Node.FOR_STATEMENT,
            Node.EXPRESSION_CASE, Node.TYPE_CASE, Node.COMMUNICATION_CASE,
        })

    @classmethod
    def nesting_nodes(cls) -> frozenset[str]:
        return frozenset({
            Node.IF_STATEMENT,
            Node.FOR_STATEMENT,
            Node.EXPRESSION_SWITCH_STATEMENT,
            Node.TYPE_SWITCH_STATEMENT,
            Node.SELECT_STATEMENT,
        })

    @classmethod
    def compensating_decisions(cls) -> frozenset[str]:
        return frozenset({Node.EXPRESSION_CASE, Node.TYPE_CASE, Node.COMMUNICATION_CASE})

    @classmethod
    def boolean_op_node(cls) -> str | None:
        return Node.BINARY_EXPRESSION

    @classmethod
    def boolean_op_operators(cls) -> frozenset[str] | None:
        return frozenset({"&&", "||"})
