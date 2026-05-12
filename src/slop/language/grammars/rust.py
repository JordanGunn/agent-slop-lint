"""Rust grammar — impl blocks + traits + free functions.

Inheritance-shaped queries (which Rust lacks) raise
``NotImplementedError`` if a rule reaches for them. The criterion for
``ObjectOriented`` membership is named scopes containing methods with
implicit receivers, not the full OOP suite.
"""
from __future__ import annotations

from typing import ClassVar

from ..multipurpose import MultiPurpose


class Rust(MultiPurpose):
    id: ClassVar[str] = "rust"

    @classmethod
    def callable(cls) -> frozenset[str]:
        return frozenset({"function_item"})

    @classmethod
    def classes(cls) -> frozenset[str]:
        return frozenset({"struct_item", "trait_item", "impl_item"})

    @classmethod
    def identifiers(cls) -> frozenset[str]:
        return frozenset({"identifier", "field_identifier", "type_identifier"})

    @classmethod
    def decision_nodes(cls) -> frozenset[str]:
        return frozenset({
            "if_expression",
            "while_expression", "for_expression",
            "match_arm",
        })

    @classmethod
    def nesting_nodes(cls) -> frozenset[str]:
        return frozenset({
            "if_expression",
            "while_expression", "for_expression",
            "match_expression",         # container for match_arm
        })

    @classmethod
    def compensating_decisions(cls) -> frozenset[str]:
        return frozenset({"match_arm"})

    @classmethod
    def boolean_op_node(cls) -> str | None:
        return "binary_expression"

    @classmethod
    def boolean_op_operators(cls) -> frozenset[str] | None:
        return frozenset({"&&", "||"})
