"""Rust grammar — impl blocks + traits + free functions.

Inheritance-shaped queries (which Rust lacks) raise
``NotImplementedError`` if a rule reaches for them. The criterion for
``ObjectOriented`` membership is named scopes containing methods with
implicit receivers, not the full OOP suite.
"""
from __future__ import annotations

from typing import ClassVar

from ..ast import Callable, Conditional, Identifier, Loop, Operator, Scope, Switch
from ..multipurpose import MultiPurpose


class Rust(MultiPurpose):
    id: ClassVar[str] = "rust"

    @classmethod
    def callable(cls) -> frozenset[str]:
        return frozenset({Callable.FUNCTION_ITEM})

    @classmethod
    def classes(cls) -> frozenset[str]:
        return frozenset({Scope.STRUCT_ITEM, Scope.TRAIT_ITEM, Scope.IMPL_ITEM})

    @classmethod
    def identifiers(cls) -> frozenset[str]:
        return frozenset({
            Identifier.IDENTIFIER, Identifier.FIELD_IDENTIFIER, Identifier.TYPE_IDENTIFIER,
        })

    @classmethod
    def decision_nodes(cls) -> frozenset[str]:
        return frozenset({
            Conditional.IF_EXPRESSION,
            Loop.WHILE_EXPRESSION, Loop.FOR_EXPRESSION,
            Switch.MATCH_ARM,
        })

    @classmethod
    def nesting_nodes(cls) -> frozenset[str]:
        return frozenset({
            Conditional.IF_EXPRESSION,
            Loop.WHILE_EXPRESSION, Loop.FOR_EXPRESSION,
            Switch.MATCH_EXPRESSION,                # container for match_arm
        })

    @classmethod
    def compensating_decisions(cls) -> frozenset[str]:
        return frozenset({Switch.MATCH_ARM})

    @classmethod
    def boolean_op_node(cls) -> str | None:
        return Operator.BINARY_EXPRESSION

    @classmethod
    def boolean_op_operators(cls) -> frozenset[str] | None:
        return frozenset({"&&", "||"})
