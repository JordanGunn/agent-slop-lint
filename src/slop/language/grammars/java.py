"""Java grammar — class-only (no free functions; `static` lives in a class)."""
from __future__ import annotations

from typing import ClassVar

from ..ast import Callable, Catch, Conditional, Literal, Loop, Operator, Scope, Switch
from ..objectoriented import ObjectOriented


class Java(ObjectOriented):
    id: ClassVar[str] = "java"

    @classmethod
    def callable(cls) -> frozenset[str]:
        return frozenset({Callable.METHOD_DECLARATION, Callable.CONSTRUCTOR_DECLARATION})

    @classmethod
    def classes(cls) -> frozenset[str]:
        return frozenset({
            Scope.CLASS_DECLARATION, Scope.INTERFACE_DECLARATION, Scope.RECORD_DECLARATION,
        })

    @classmethod
    def decision_nodes(cls) -> frozenset[str]:
        return frozenset({
            Conditional.IF_STATEMENT,
            Loop.FOR_STATEMENT, Loop.ENHANCED_FOR_STATEMENT,
            Loop.WHILE_STATEMENT, Loop.DO_STATEMENT,
            Switch.SWITCH_LABEL,            # case label in classic switch_statement
            Switch.SWITCH_RULE,             # arrow rule in modern switch_expression
            Catch.CATCH_CLAUSE,
            Conditional.TERNARY_EXPRESSION,
        })

    @classmethod
    def nesting_nodes(cls) -> frozenset[str]:
        return frozenset({
            Conditional.IF_STATEMENT,
            Loop.FOR_STATEMENT, Loop.ENHANCED_FOR_STATEMENT,
            Loop.WHILE_STATEMENT, Loop.DO_STATEMENT,
            Switch.SWITCH_STATEMENT,        # classic container
            Switch.SWITCH_EXPRESSION,       # Java 14+ container
            Catch.CATCH_CLAUSE,
            Conditional.TERNARY_EXPRESSION,
        })

    @classmethod
    def compensating_decisions(cls) -> frozenset[str]:
        return frozenset({Switch.SWITCH_LABEL, Switch.SWITCH_RULE})

    @classmethod
    def boolean_op_node(cls) -> str | None:
        return Operator.BINARY_EXPRESSION

    @classmethod
    def boolean_op_operators(cls) -> frozenset[str] | None:
        return frozenset({"&&", "||"})

    @classmethod
    def numeric_literal_nodes(cls) -> frozenset[str]:
        return frozenset({
            Literal.DECIMAL_INTEGER_LITERAL,
            Literal.DECIMAL_FLOATING_POINT_LITERAL,
            Literal.HEX_INTEGER_LITERAL,
            Literal.OCTAL_INTEGER_LITERAL,
        })

    @classmethod
    def operator_nodes(cls) -> frozenset[str]:
        return frozenset({
            "if", "else", "for", "while", "do", "return",
            "class", "interface", "enum", "extends", "implements",
            "import", "package", "try", "catch", "finally",
            "throw", "throws", "new", "instanceof", "switch",
            "case", "default", "break", "continue",
            "public", "private", "protected", "static", "final",
            "abstract", "synchronized", "volatile",
            "void", "super", "this",
            "=", "+", "-", "*", "/", "%",
            "==", "!=", "<", ">", "<=", ">=",
            "&&", "||", "!", "~", "&", "|", "^", "<<", ">>", ">>>",
            "+=", "-=", "*=", "/=", "%=",
            "++", "--", "?", "->",
        })

    @classmethod
    def operand_nodes(cls) -> frozenset[str]:
        return frozenset({
            "identifier", "type_identifier", "field_identifier",
            "decimal_integer_literal", "hex_integer_literal",
            "octal_integer_literal", "binary_integer_literal",
            "decimal_floating_point_literal",
            "string_literal", "string_fragment",
            "character_literal",
            "true", "false", "null",
        })
