"""Go grammar — struct + receiver-bound methods + free functions.

Tree-sitter-go syntactically distinguishes ``function_declaration``
(free) from ``method_declaration`` (receiver). Both are callables;
``functions()`` and ``methods()`` return distinct subsets.
"""
from __future__ import annotations

from typing import ClassVar

from ..multipurpose import MultiPurpose


class Go(MultiPurpose):
    id: ClassVar[str] = "go"

    @classmethod
    def callable(cls) -> frozenset[str]:
        return frozenset({"function_declaration", "method_declaration", "func_literal"})

    @classmethod
    def classes(cls) -> frozenset[str]:
        # Go doesn't have classes; struct + interface are the closest.
        return frozenset({"type_declaration"})

    @classmethod
    def identifiers(cls) -> frozenset[str]:
        return frozenset({"identifier", "field_identifier", "type_identifier"})

    @classmethod
    def functions(cls) -> frozenset[str]:
        return frozenset({"function_declaration", "func_literal"})

    @classmethod
    def methods(cls) -> frozenset[str]:
        return frozenset({"method_declaration"})

    @classmethod
    def decision_nodes(cls) -> frozenset[str]:
        return frozenset({
            "if_statement",
            "for_statement",
            "expression_case", "type_case", "communication_case",
        })

    @classmethod
    def nesting_nodes(cls) -> frozenset[str]:
        return frozenset({
            "if_statement",
            "for_statement",
            "expression_switch_statement",
            "type_switch_statement",
            "select_statement",
        })

    @classmethod
    def compensating_decisions(cls) -> frozenset[str]:
        return frozenset({"expression_case", "type_case", "communication_case"})

    @classmethod
    def boolean_op_node(cls) -> str | None:
        return "binary_expression"

    @classmethod
    def boolean_op_operators(cls) -> frozenset[str] | None:
        return frozenset({"&&", "||"})
