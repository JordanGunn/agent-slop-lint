"""Rust grammar — impl blocks + traits + free functions.

Inheritance-shaped queries (which Rust lacks) raise
``NotImplementedError`` if a rule reaches for them. The criterion for
``ObjectOriented`` membership is named scopes containing methods with
implicit receivers, not the full OOP suite.
"""
from __future__ import annotations

from typing import ClassVar

from ..ast import Node
from ..multipurpose import MultiPurpose


class Rust(MultiPurpose):
    id: ClassVar[str] = "rust"

    @classmethod
    def callable(cls) -> frozenset[str]:
        return frozenset({Node.FUNCTION_ITEM})

    @classmethod
    def classes(cls) -> frozenset[str]:
        return frozenset({Node.STRUCT_ITEM, Node.TRAIT_ITEM, Node.IMPL_ITEM})

    @classmethod
    def identifiers(cls) -> frozenset[str]:
        return frozenset({Node.IDENTIFIER, Node.FIELD_IDENTIFIER, Node.TYPE_IDENTIFIER})

    @classmethod
    def decision_nodes(cls) -> frozenset[str]:
        return frozenset({
            Node.IF_EXPRESSION,
            Node.WHILE_EXPRESSION, Node.FOR_EXPRESSION,
            Node.MATCH_ARM,
        })

    @classmethod
    def nesting_nodes(cls) -> frozenset[str]:
        return frozenset({
            Node.IF_EXPRESSION,
            Node.WHILE_EXPRESSION, Node.FOR_EXPRESSION,
            Node.MATCH_EXPRESSION,          # container for match_arm
        })

    @classmethod
    def compensating_decisions(cls) -> frozenset[str]:
        return frozenset({Node.MATCH_ARM})

    @classmethod
    def boolean_op_node(cls) -> str | None:
        return Node.BINARY_EXPRESSION

    @classmethod
    def boolean_op_operators(cls) -> frozenset[str] | None:
        return frozenset({"&&", "||"})
