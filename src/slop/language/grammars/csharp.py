"""C# grammar — class-only (no top-level free functions historically)."""
from __future__ import annotations

from typing import ClassVar

from ..ast import Callable, Catch, Conditional, Literal, Loop, Operator, Scope, Switch
from ..objectoriented import ObjectOriented


class CSharp(ObjectOriented):
    id: ClassVar[str] = "c_sharp"

    @classmethod
    def callable(cls) -> frozenset[str]:
        return frozenset({
            Callable.METHOD_DECLARATION, Callable.CONSTRUCTOR_DECLARATION,
            Callable.LOCAL_FUNCTION_STATEMENT,
        })

    @classmethod
    def classes(cls) -> frozenset[str]:
        return frozenset({
            Scope.CLASS_DECLARATION, Scope.INTERFACE_DECLARATION, Scope.STRUCT_DECLARATION,
        })

    @classmethod
    def decision_nodes(cls) -> frozenset[str]:
        return frozenset({
            Conditional.IF_STATEMENT,
            Loop.FOR_STATEMENT, Loop.FOREACH_STATEMENT,
            Loop.WHILE_STATEMENT, Loop.DO_STATEMENT,
            Switch.SWITCH_SECTION,
            Catch.CATCH_CLAUSE,
            Conditional.CONDITIONAL_EXPRESSION,
        })

    @classmethod
    def nesting_nodes(cls) -> frozenset[str]:
        return frozenset({
            Conditional.IF_STATEMENT,
            Loop.FOR_STATEMENT, Loop.FOREACH_STATEMENT,
            Loop.WHILE_STATEMENT, Loop.DO_STATEMENT,
            Switch.SWITCH_STATEMENT,
            Catch.CATCH_CLAUSE,
            Conditional.CONDITIONAL_EXPRESSION,
        })

    @classmethod
    def compensating_decisions(cls) -> frozenset[str]:
        return frozenset({Switch.SWITCH_SECTION})

    @classmethod
    def boolean_op_node(cls) -> str | None:
        return Operator.BINARY_EXPRESSION

    @classmethod
    def boolean_op_operators(cls) -> frozenset[str] | None:
        return frozenset({"&&", "||"})

    @classmethod
    def numeric_literal_nodes(cls) -> frozenset[str]:
        return frozenset({Literal.INTEGER_LITERAL, Literal.REAL_LITERAL})
