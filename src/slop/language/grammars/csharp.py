"""C# grammar — class-only (no top-level free functions historically)."""
from __future__ import annotations

from typing import ClassVar

from ..ast import Node
from ..objectoriented import ObjectOriented


class CSharp(ObjectOriented):
    id: ClassVar[str] = "c_sharp"

    @classmethod
    def callable(cls) -> frozenset[str]:
        return frozenset({
            Node.METHOD_DECLARATION, Node.CONSTRUCTOR_DECLARATION,
            Node.LOCAL_FUNCTION_STATEMENT,
        })

    @classmethod
    def classes(cls) -> frozenset[str]:
        return frozenset({
            Node.CLASS_DECLARATION, Node.INTERFACE_DECLARATION, Node.STRUCT_DECLARATION,
        })

    @classmethod
    def decision_nodes(cls) -> frozenset[str]:
        return frozenset({
            Node.IF_STATEMENT,
            Node.FOR_STATEMENT, Node.FOREACH_STATEMENT,
            Node.WHILE_STATEMENT, Node.DO_STATEMENT,
            Node.SWITCH_SECTION,
            Node.CATCH_CLAUSE,
            Node.CONDITIONAL_EXPRESSION,
        })

    @classmethod
    def nesting_nodes(cls) -> frozenset[str]:
        return frozenset({
            Node.IF_STATEMENT,
            Node.FOR_STATEMENT, Node.FOREACH_STATEMENT,
            Node.WHILE_STATEMENT, Node.DO_STATEMENT,
            Node.SWITCH_STATEMENT,
            Node.CATCH_CLAUSE,
            Node.CONDITIONAL_EXPRESSION,
        })

    @classmethod
    def compensating_decisions(cls) -> frozenset[str]:
        return frozenset({Node.SWITCH_SECTION})

    @classmethod
    def boolean_op_node(cls) -> str | None:
        return Node.BINARY_EXPRESSION

    @classmethod
    def boolean_op_operators(cls) -> frozenset[str] | None:
        return frozenset({"&&", "||"})
