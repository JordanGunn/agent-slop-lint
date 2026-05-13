"""C# grammar — class-only (no top-level free functions historically)."""
from __future__ import annotations

from typing import Any, ClassVar

from ..ast import Callable, Catch, Conditional, Literal, Loop, Operator, Scope, Switch
from ..objectoriented import ObjectOriented


class CSharp(ObjectOriented):
    id: ClassVar[str] = "c_sharp"

    @classmethod
    def callable(cls) -> frozenset[str]:
        return frozenset({
            Callable.METHOD_DECLARATION, Callable.CONSTRUCTOR_DECLARATION,
            Callable.LOCAL_FUNCTION_STATEMENT,
        })

    @classmethod
    def classes(cls) -> frozenset[str]:
        return frozenset({
            Scope.CLASS_DECLARATION, Scope.INTERFACE_DECLARATION, Scope.STRUCT_DECLARATION,
        })

    @classmethod
    def decision_nodes(cls) -> frozenset[str]:
        return frozenset({
            Conditional.IF_STATEMENT,
            Loop.FOR_STATEMENT, Loop.FOREACH_STATEMENT,
            Loop.WHILE_STATEMENT, Loop.DO_STATEMENT,
            Switch.SWITCH_SECTION,
            Catch.CATCH_CLAUSE,
            Conditional.CONDITIONAL_EXPRESSION,
        })

    @classmethod
    def nesting_nodes(cls) -> frozenset[str]:
        return frozenset({
            Conditional.IF_STATEMENT,
            Loop.FOR_STATEMENT, Loop.FOREACH_STATEMENT,
            Loop.WHILE_STATEMENT, Loop.DO_STATEMENT,
            Switch.SWITCH_STATEMENT,
            Catch.CATCH_CLAUSE,
            Conditional.CONDITIONAL_EXPRESSION,
        })

    @classmethod
    def compensating_decisions(cls) -> frozenset[str]:
        return frozenset({Switch.SWITCH_SECTION})

    @classmethod
    def boolean_op_node(cls) -> str | None:
        return Operator.BINARY_EXPRESSION

    @classmethod
    def boolean_op_operators(cls) -> frozenset[str] | None:
        return frozenset({"&&", "||"})

    @classmethod
    def numeric_literal_nodes(cls) -> frozenset[str]:
        return frozenset({Literal.INTEGER_LITERAL, Literal.REAL_LITERAL})

    @classmethod
    def operator_nodes(cls) -> frozenset[str]:
        return frozenset({
            "if", "else", "for", "foreach", "while", "do", "return",
            "class", "struct", "interface", "enum",
            "using", "namespace", "try", "catch", "finally",
            "throw", "new", "is", "as", "switch", "in",
            "case", "default", "break", "continue",
            "public", "private", "protected", "internal", "static",
            "readonly", "abstract", "virtual", "override", "sealed",
            "async", "await", "void", "this", "base", "var",
            "=", "+", "-", "*", "/", "%",
            "==", "!=", "<", ">", "<=", ">=",
            "&&", "||", "!", "~", "&", "|", "^", "<<", ">>",
            "+=", "-=", "*=", "/=", "%=",
            "++", "--", "?", "=>", "??",
        })

    @classmethod
    def operand_nodes(cls) -> frozenset[str]:
        return frozenset({
            "identifier", "type_identifier",
            "integer_literal", "real_literal",
            "string_literal", "verbatim_string_literal",
            "interpolated_string_expression",
            "character_literal",
            "true", "false", "null",
        })

    @classmethod
    def extract_superclasses(cls, node: Any, content: bytes) -> list[str]:
        """C#: ``base_list`` child holds identifier classes + interfaces."""
        out: list[str] = []
        for child in node.children:
            if child.type == "base_list":
                for gc in child.children:
                    if gc.type == "identifier":
                        out.append(content[gc.start_byte:gc.end_byte].decode("utf-8", errors="replace"))
        return out
