"""JavaScript grammar — classes + free functions + arrow functions.

Tree-sitter-javascript syntactically distinguishes ``function_declaration``
and ``arrow_function`` (free) from ``method_definition`` (class-bound).
"""
from __future__ import annotations

from typing import ClassVar

from ..ast import Node
from ..multipurpose import MultiPurpose


class JavaScript(MultiPurpose):
    id: ClassVar[str] = "javascript"

    @classmethod
    def callable(cls) -> frozenset[str]:
        return frozenset({
            Node.FUNCTION_DECLARATION, Node.FUNCTION_EXPRESSION,
            Node.ARROW_FUNCTION, Node.METHOD_DEFINITION,
            Node.GENERATOR_FUNCTION_DECLARATION,
        })

    @classmethod
    def classes(cls) -> frozenset[str]:
        return frozenset({Node.CLASS_DECLARATION})

    @classmethod
    def identifiers(cls) -> frozenset[str]:
        return frozenset({Node.IDENTIFIER, Node.PROPERTY_IDENTIFIER})

    @classmethod
    def functions(cls) -> frozenset[str]:
        return frozenset({
            Node.FUNCTION_DECLARATION, Node.FUNCTION_EXPRESSION,
            Node.ARROW_FUNCTION, Node.GENERATOR_FUNCTION_DECLARATION,
        })

    @classmethod
    def methods(cls) -> frozenset[str]:
        return frozenset({Node.METHOD_DEFINITION})

    @classmethod
    def decision_nodes(cls) -> frozenset[str]:
        return frozenset({
            Node.IF_STATEMENT,
            Node.FOR_STATEMENT, Node.FOR_IN_STATEMENT, Node.FOR_OF_STATEMENT,
            Node.WHILE_STATEMENT, Node.DO_STATEMENT,
            Node.SWITCH_CASE,
            Node.CATCH_CLAUSE,
            Node.TERNARY_EXPRESSION,
        })

    @classmethod
    def nesting_nodes(cls) -> frozenset[str]:
        return frozenset({
            Node.IF_STATEMENT,
            Node.FOR_STATEMENT, Node.FOR_IN_STATEMENT, Node.FOR_OF_STATEMENT,
            Node.WHILE_STATEMENT, Node.DO_STATEMENT,
            Node.SWITCH_STATEMENT,          # container for switch_case
            Node.CATCH_CLAUSE,
            Node.TERNARY_EXPRESSION,
        })

    @classmethod
    def compensating_decisions(cls) -> frozenset[str]:
        return frozenset({Node.SWITCH_CASE})

    @classmethod
    def boolean_op_node(cls) -> str | None:
        return Node.BINARY_EXPRESSION

    @classmethod
    def boolean_op_operators(cls) -> frozenset[str] | None:
        return frozenset({"&&", "||", "??"})
