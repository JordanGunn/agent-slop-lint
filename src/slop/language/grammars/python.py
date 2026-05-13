"""Python grammar — class-and-function-emitting, multi-paradigm."""
from __future__ import annotations

from typing import Any, ClassVar

from ..ast import Callable, Catch, Conditional, Literal, Loop, Operator, Scope, Switch
from ..multipurpose import MultiPurpose


class Python(MultiPurpose):
    id: ClassVar[str] = "python"

    @classmethod
    def callable(cls) -> frozenset[str]:
        return frozenset({
            Callable.FUNCTION_DEFINITION,
            Callable.ASYNC_FUNCTION_DEFINITION,
            Callable.LAMBDA,
        })

    @classmethod
    def classes(cls) -> frozenset[str]:
        return frozenset({Scope.CLASS_DEFINITION})

    @classmethod
    def methods(cls) -> frozenset[str]:
        # Lambdas can't be methods in Python (no `def` inside class via lambda).
        return frozenset({Callable.FUNCTION_DEFINITION, Callable.ASYNC_FUNCTION_DEFINITION})

    @classmethod
    def decision_nodes(cls) -> frozenset[str]:
        return frozenset({
            Conditional.IF_STATEMENT, Conditional.ELIF_CLAUSE,
            Loop.FOR_STATEMENT, Loop.WHILE_STATEMENT,
            Catch.EXCEPT_CLAUSE,
            Conditional.CONDITIONAL_EXPRESSION,    # x if cond else y
            Switch.CASE_CLAUSE,                    # match/case (PEP 634)
        })

    @classmethod
    def nesting_nodes(cls) -> frozenset[str]:
        return frozenset({
            Conditional.IF_STATEMENT,
            Loop.FOR_STATEMENT, Loop.WHILE_STATEMENT,
            Catch.EXCEPT_CLAUSE,
            Conditional.CONDITIONAL_EXPRESSION,
            Switch.MATCH_STATEMENT,                # container for case_clause
        })

    @classmethod
    def compensating_decisions(cls) -> frozenset[str]:
        return frozenset({
            Conditional.ELIF_CLAUSE,               # syntactically inside if_statement
            Switch.CASE_CLAUSE,                    # syntactically inside match_statement
        })

    @classmethod
    def boolean_op_node(cls) -> str | None:
        return Operator.BOOLEAN_OPERATOR

    # boolean_op_operators defaults to None — Python's dedicated
    # boolean_operator node always counts (and/or).

    @classmethod
    def numeric_literal_nodes(cls) -> frozenset[str]:
        return frozenset({Literal.INTEGER, Literal.FLOAT})

    @classmethod
    def operator_nodes(cls) -> frozenset[str]:
        return frozenset({
            # Keywords
            "def", "if", "else", "elif", "for", "while", "return",
            "class", "import", "from", "try", "except", "finally",
            "raise", "with", "as", "yield", "lambda", "del", "assert",
            "break", "continue", "pass", "and", "or", "not", "in", "is",
            # Operator symbols
            "=", "+", "-", "*", "/", "**", "//", "%",
            "==", "!=", "<", ">", "<=", ">=",
            "|", "&", "^", "~", "<<", ">>",
            "+=", "-=", "*=", "/=", "//=", "%=", "**=",
            "->", "@",
        })

    @classmethod
    def operand_nodes(cls) -> frozenset[str]:
        return frozenset({
            "identifier", "integer", "float", "string",
            "true", "false", "none", "type",
        })

    @classmethod
    def extract_superclasses(cls, node: Any, content: bytes) -> list[str]:
        """Python: ``class Foo(Bar, Mixin):`` — superclasses field."""
        sc_node = node.child_by_field_name("superclasses")
        if sc_node is None:
            return []
        out: list[str] = []
        for child in sc_node.children:
            if child.type == "identifier":
                out.append(content[child.start_byte:child.end_byte].decode("utf-8", errors="replace"))
            elif child.type == "attribute":
                text = content[child.start_byte:child.end_byte].decode("utf-8", errors="replace")
                out.append(text.split(".")[-1])
        return out
