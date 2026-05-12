"""Java grammar — class-only (no free functions; `static` lives in a class)."""
from __future__ import annotations

from typing import ClassVar

from ..objectoriented import ObjectOriented


class Java(ObjectOriented):
    id: ClassVar[str] = "java"

    @classmethod
    def callable(cls) -> frozenset[str]:
        return frozenset({"method_declaration", "constructor_declaration"})

    @classmethod
    def classes(cls) -> frozenset[str]:
        return frozenset({"class_declaration", "interface_declaration", "record_declaration"})

    @classmethod
    def decision_nodes(cls) -> frozenset[str]:
        return frozenset({
            "if_statement",
            "for_statement", "enhanced_for_statement",
            "while_statement", "do_statement",
            "switch_label",             # case label in classic switch_statement
            "switch_rule",              # arrow rule in modern switch_expression
            "catch_clause",
            "ternary_expression",
        })

    @classmethod
    def nesting_nodes(cls) -> frozenset[str]:
        return frozenset({
            "if_statement",
            "for_statement", "enhanced_for_statement",
            "while_statement", "do_statement",
            "switch_statement",         # classic container
            "switch_expression",        # Java 14+ container
            "catch_clause",
            "ternary_expression",
        })

    @classmethod
    def compensating_decisions(cls) -> frozenset[str]:
        return frozenset({"switch_label", "switch_rule"})

    @classmethod
    def boolean_op_node(cls) -> str | None:
        return "binary_expression"

    @classmethod
    def boolean_op_operators(cls) -> frozenset[str] | None:
        return frozenset({"&&", "||"})
