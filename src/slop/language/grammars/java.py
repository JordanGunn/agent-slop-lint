"""Java grammar — class-only (no free functions; `static` lives in a class)."""
from __future__ import annotations

from typing import ClassVar

from ..ast import Node
from ..objectoriented import ObjectOriented


class Java(ObjectOriented):
    id: ClassVar[str] = "java"

    @classmethod
    def callable(cls) -> frozenset[str]:
        return frozenset({Node.METHOD_DECLARATION, Node.CONSTRUCTOR_DECLARATION})

    @classmethod
    def classes(cls) -> frozenset[str]:
        return frozenset({
            Node.CLASS_DECLARATION, Node.INTERFACE_DECLARATION, Node.RECORD_DECLARATION,
        })

    @classmethod
    def decision_nodes(cls) -> frozenset[str]:
        return frozenset({
            Node.IF_STATEMENT,
            Node.FOR_STATEMENT, Node.ENHANCED_FOR_STATEMENT,
            Node.WHILE_STATEMENT, Node.DO_STATEMENT,
            Node.SWITCH_LABEL,              # case label in classic switch_statement
            Node.SWITCH_RULE,               # arrow rule in modern switch_expression
            Node.CATCH_CLAUSE,
            Node.TERNARY_EXPRESSION,
        })

    @classmethod
    def nesting_nodes(cls) -> frozenset[str]:
        return frozenset({
            Node.IF_STATEMENT,
            Node.FOR_STATEMENT, Node.ENHANCED_FOR_STATEMENT,
            Node.WHILE_STATEMENT, Node.DO_STATEMENT,
            Node.SWITCH_STATEMENT,          # classic container
            Node.SWITCH_EXPRESSION,         # Java 14+ container
            Node.CATCH_CLAUSE,
            Node.TERNARY_EXPRESSION,
        })

    @classmethod
    def compensating_decisions(cls) -> frozenset[str]:
        return frozenset({Node.SWITCH_LABEL, Node.SWITCH_RULE})

    @classmethod
    def boolean_op_node(cls) -> str | None:
        return Node.BINARY_EXPRESSION

    @classmethod
    def boolean_op_operators(cls) -> frozenset[str] | None:
        return frozenset({"&&", "||"})
