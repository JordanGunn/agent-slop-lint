"""TypeScript grammar — classes + interfaces + free functions.

Like JavaScript, syntactically distinguishes function/method node types.
"""
from __future__ import annotations

from typing import ClassVar

from ..ast import Callable, Catch, Conditional, Identifier, Literal, Loop, Operator, Scope, Switch
from ..multipurpose import MultiPurpose


class TypeScript(MultiPurpose):
    id: ClassVar[str] = "typescript"

    @classmethod
    def callable(cls) -> frozenset[str]:
        return frozenset({
            Callable.FUNCTION_DECLARATION, Callable.FUNCTION_EXPRESSION,
            Callable.ARROW_FUNCTION, Callable.METHOD_DEFINITION,
            Callable.GENERATOR_FUNCTION_DECLARATION,
        })

    @classmethod
    def classes(cls) -> frozenset[str]:
        return frozenset({Scope.CLASS_DECLARATION, Scope.INTERFACE_DECLARATION})

    @classmethod
    def identifiers(cls) -> frozenset[str]:
        return frozenset({
            Identifier.IDENTIFIER, Identifier.PROPERTY_IDENTIFIER, Identifier.TYPE_IDENTIFIER,
        })

    @classmethod
    def functions(cls) -> frozenset[str]:
        return frozenset({
            Callable.FUNCTION_DECLARATION, Callable.FUNCTION_EXPRESSION,
            Callable.ARROW_FUNCTION, Callable.GENERATOR_FUNCTION_DECLARATION,
        })

    @classmethod
    def methods(cls) -> frozenset[str]:
        return frozenset({Callable.METHOD_DEFINITION})

    @classmethod
    def decision_nodes(cls) -> frozenset[str]:
        return frozenset({
            Conditional.IF_STATEMENT,
            Loop.FOR_STATEMENT, Loop.FOR_IN_STATEMENT, Loop.FOR_OF_STATEMENT,
            Loop.WHILE_STATEMENT, Loop.DO_STATEMENT,
            Switch.SWITCH_CASE,
            Catch.CATCH_CLAUSE,
            Conditional.TERNARY_EXPRESSION,
        })

    @classmethod
    def nesting_nodes(cls) -> frozenset[str]:
        return frozenset({
            Conditional.IF_STATEMENT,
            Loop.FOR_STATEMENT, Loop.FOR_IN_STATEMENT, Loop.FOR_OF_STATEMENT,
            Loop.WHILE_STATEMENT, Loop.DO_STATEMENT,
            Switch.SWITCH_STATEMENT,
            Catch.CATCH_CLAUSE,
            Conditional.TERNARY_EXPRESSION,
        })

    @classmethod
    def compensating_decisions(cls) -> frozenset[str]:
        return frozenset({Switch.SWITCH_CASE})

    @classmethod
    def boolean_op_node(cls) -> str | None:
        return Operator.BINARY_EXPRESSION

    @classmethod
    def boolean_op_operators(cls) -> frozenset[str] | None:
        return frozenset({"&&", "||", "??"})

    @classmethod
    def numeric_literal_nodes(cls) -> frozenset[str]:
        return frozenset({Literal.NUMBER})
