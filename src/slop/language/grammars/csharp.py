"""C# grammar — class-only (no top-level free functions historically)."""
from __future__ import annotations

from typing import ClassVar

from ..objectoriented import ObjectOriented


class CSharp(ObjectOriented):
    id: ClassVar[str] = "c_sharp"

    @classmethod
    def callable(cls) -> frozenset[str]:
        return frozenset({
            "method_declaration", "constructor_declaration",
            "local_function_statement",
        })

    @classmethod
    def classes(cls) -> frozenset[str]:
        return frozenset({"class_declaration", "interface_declaration", "struct_declaration"})

    @classmethod
    def decision_nodes(cls) -> frozenset[str]:
        return frozenset({
            "if_statement",
            "for_statement", "foreach_statement",
            "while_statement", "do_statement",
            "switch_section",
            "catch_clause",
            "conditional_expression",
        })

    @classmethod
    def nesting_nodes(cls) -> frozenset[str]:
        return frozenset({
            "if_statement",
            "for_statement", "foreach_statement",
            "while_statement", "do_statement",
            "switch_statement",
            "catch_clause",
            "conditional_expression",
        })

    @classmethod
    def compensating_decisions(cls) -> frozenset[str]:
        return frozenset({"switch_section"})

    @classmethod
    def boolean_op_node(cls) -> str | None:
        return "binary_expression"

    @classmethod
    def boolean_op_operators(cls) -> frozenset[str] | None:
        return frozenset({"&&", "||"})
