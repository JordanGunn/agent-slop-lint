"""Python grammar — class-and-function-emitting, multi-paradigm."""
from __future__ import annotations

from typing import ClassVar

from ..ast import Node
from ..multipurpose import MultiPurpose


class Python(MultiPurpose):
    id: ClassVar[str] = "python"

    @classmethod
    def callable(cls) -> frozenset[str]:
        return frozenset({
            Node.FUNCTION_DEFINITION,
            Node.ASYNC_FUNCTION_DEFINITION,
            Node.LAMBDA,
        })

    @classmethod
    def classes(cls) -> frozenset[str]:
        return frozenset({Node.CLASS_DEFINITION})

    @classmethod
    def methods(cls) -> frozenset[str]:
        # Lambdas can't be methods in Python (no `def` inside class via lambda).
        return frozenset({Node.FUNCTION_DEFINITION, Node.ASYNC_FUNCTION_DEFINITION})

    @classmethod
    def decision_nodes(cls) -> frozenset[str]:
        return frozenset({
            Node.IF_STATEMENT, Node.ELIF_CLAUSE,
            Node.FOR_STATEMENT, Node.WHILE_STATEMENT,
            Node.EXCEPT_CLAUSE,
            Node.CONDITIONAL_EXPRESSION,    # x if cond else y
            Node.CASE_CLAUSE,               # match/case (PEP 634)
        })

    @classmethod
    def nesting_nodes(cls) -> frozenset[str]:
        return frozenset({
            Node.IF_STATEMENT,
            Node.FOR_STATEMENT, Node.WHILE_STATEMENT,
            Node.EXCEPT_CLAUSE,
            Node.CONDITIONAL_EXPRESSION,
            Node.MATCH_STATEMENT,           # container for case_clause
        })

    @classmethod
    def compensating_decisions(cls) -> frozenset[str]:
        return frozenset({
            Node.ELIF_CLAUSE,               # syntactically inside if_statement
            Node.CASE_CLAUSE,               # syntactically inside match_statement
        })

    @classmethod
    def boolean_op_node(cls) -> str | None:
        return Node.BOOLEAN_OPERATOR

    # boolean_op_operators defaults to None — Python's dedicated
    # boolean_operator node always counts (and/or).
