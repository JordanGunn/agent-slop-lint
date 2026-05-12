"""Go grammar — struct + receiver-bound methods + free functions.

Tree-sitter-go syntactically distinguishes ``function_declaration``
(free) from ``method_declaration`` (receiver). Both are callables;
``functions()`` and ``methods()`` return distinct subsets.
"""
from __future__ import annotations

from typing import ClassVar

from ..ast import Callable, Conditional, Identifier, Literal, Loop, Operator, Scope, Switch
from ..multipurpose import MultiPurpose


class Go(MultiPurpose):
    id: ClassVar[str] = "go"

    @classmethod
    def callable(cls) -> frozenset[str]:
        return frozenset({
            Callable.FUNCTION_DECLARATION, Callable.METHOD_DECLARATION, Callable.FUNC_LITERAL,
        })

    @classmethod
    def classes(cls) -> frozenset[str]:
        # Go doesn't have classes; struct + interface are the closest.
        return frozenset({Scope.TYPE_DECLARATION})

    @classmethod
    def identifiers(cls) -> frozenset[str]:
        return frozenset({
            Identifier.IDENTIFIER, Identifier.FIELD_IDENTIFIER, Identifier.TYPE_IDENTIFIER,
        })

    @classmethod
    def functions(cls) -> frozenset[str]:
        return frozenset({Callable.FUNCTION_DECLARATION, Callable.FUNC_LITERAL})

    @classmethod
    def methods(cls) -> frozenset[str]:
        return frozenset({Callable.METHOD_DECLARATION})

    @classmethod
    def decision_nodes(cls) -> frozenset[str]:
        return frozenset({
            Conditional.IF_STATEMENT,
            Loop.FOR_STATEMENT,
            Switch.EXPRESSION_CASE, Switch.TYPE_CASE, Switch.COMMUNICATION_CASE,
        })

    @classmethod
    def nesting_nodes(cls) -> frozenset[str]:
        return frozenset({
            Conditional.IF_STATEMENT,
            Loop.FOR_STATEMENT,
            Switch.EXPRESSION_SWITCH_STATEMENT,
            Switch.TYPE_SWITCH_STATEMENT,
            Switch.SELECT_STATEMENT,
        })

    @classmethod
    def compensating_decisions(cls) -> frozenset[str]:
        return frozenset({
            Switch.EXPRESSION_CASE, Switch.TYPE_CASE, Switch.COMMUNICATION_CASE,
        })

    @classmethod
    def boolean_op_node(cls) -> str | None:
        return Operator.BINARY_EXPRESSION

    @classmethod
    def boolean_op_operators(cls) -> frozenset[str] | None:
        return frozenset({"&&", "||"})

    @classmethod
    def numeric_literal_nodes(cls) -> frozenset[str]:
        return frozenset({
            Literal.INT_LITERAL, Literal.FLOAT_LITERAL,
            Literal.IMAGINARY_LITERAL, Literal.RUNE_LITERAL,
        })
