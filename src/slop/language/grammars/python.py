"""Python grammar — class-and-function-emitting, multi-paradigm."""
from __future__ import annotations

from typing import ClassVar

from ..multipurpose import MultiPurpose


class Python(MultiPurpose):
    id: ClassVar[str] = "python"

    @classmethod
    def callable(cls) -> frozenset[str]:
        return frozenset({"function_definition", "async_function_definition", "lambda"})

    @classmethod
    def classes(cls) -> frozenset[str]:
        return frozenset({"class_definition"})

    @classmethod
    def methods(cls) -> frozenset[str]:
        # Lambdas can't be methods in Python (no `def` inside class via lambda).
        return frozenset({"function_definition", "async_function_definition"})

    @classmethod
    def decision_nodes(cls) -> frozenset[str]:
        return frozenset({
            "if_statement", "elif_clause",
            "for_statement", "while_statement",
            "except_clause",
            "conditional_expression",   # x if cond else y
            "case_clause",              # match/case (PEP 634)
        })

    @classmethod
    def nesting_nodes(cls) -> frozenset[str]:
        return frozenset({
            "if_statement",
            "for_statement", "while_statement",
            "except_clause",
            "conditional_expression",
            "match_statement",          # container for case_clause
        })

    @classmethod
    def compensating_decisions(cls) -> frozenset[str]:
        return frozenset({
            "elif_clause",              # syntactically inside if_statement
            "case_clause",              # syntactically inside match_statement
        })

    @classmethod
    def boolean_op_node(cls) -> str | None:
        return "boolean_operator"

    # boolean_op_operators defaults to None — Python's dedicated
    # boolean_operator node always counts (and/or).
