"""Rust grammar — impl blocks + traits + free functions.

Inheritance-shaped queries (which Rust lacks) raise
``NotImplementedError`` if a rule reaches for them. The criterion for
``ObjectOriented`` membership is named scopes containing methods with
implicit receivers, not the full OOP suite.
"""
from __future__ import annotations

from typing import ClassVar

from ..ast import Callable, Conditional, Identifier, Literal, Loop, Operator, Scope, Switch
from ..multipurpose import MultiPurpose


class Rust(MultiPurpose):
    id: ClassVar[str] = "rust"

    @classmethod
    def callable(cls) -> frozenset[str]:
        return frozenset({Callable.FUNCTION_ITEM})

    @classmethod
    def classes(cls) -> frozenset[str]:
        return frozenset({Scope.STRUCT_ITEM, Scope.TRAIT_ITEM, Scope.IMPL_ITEM})

    @classmethod
    def identifiers(cls) -> frozenset[str]:
        return frozenset({
            Identifier.IDENTIFIER, Identifier.FIELD_IDENTIFIER, Identifier.TYPE_IDENTIFIER,
        })

    @classmethod
    def decision_nodes(cls) -> frozenset[str]:
        return frozenset({
            Conditional.IF_EXPRESSION,
            Loop.WHILE_EXPRESSION, Loop.FOR_EXPRESSION,
            Switch.MATCH_ARM,
        })

    @classmethod
    def nesting_nodes(cls) -> frozenset[str]:
        return frozenset({
            Conditional.IF_EXPRESSION,
            Loop.WHILE_EXPRESSION, Loop.FOR_EXPRESSION,
            Switch.MATCH_EXPRESSION,                # container for match_arm
        })

    @classmethod
    def compensating_decisions(cls) -> frozenset[str]:
        return frozenset({Switch.MATCH_ARM})

    @classmethod
    def boolean_op_node(cls) -> str | None:
        return Operator.BINARY_EXPRESSION

    @classmethod
    def boolean_op_operators(cls) -> frozenset[str] | None:
        return frozenset({"&&", "||"})

    @classmethod
    def numeric_literal_nodes(cls) -> frozenset[str]:
        return frozenset({Literal.INTEGER_LITERAL, Literal.FLOAT_LITERAL})

    @classmethod
    def operator_nodes(cls) -> frozenset[str]:
        return frozenset({
            "fn", "if", "else", "for", "while", "loop", "match",
            "return", "break", "continue", "let", "mut", "ref",
            "struct", "enum", "impl", "trait", "type", "use", "mod",
            "pub", "self", "super", "crate", "as", "where",
            "async", "await", "unsafe", "move",
            "=", "+", "-", "*", "/", "%",
            "==", "!=", "<", ">", "<=", ">=",
            "&&", "||", "!", "&", "|", "^", "<<", ">>",
            "+=", "-=", "*=", "/=", "%=",
            "=>", "::", "..", "..=", "?",
        })

    @classmethod
    def operand_nodes(cls) -> frozenset[str]:
        return frozenset({
            "identifier", "field_identifier", "type_identifier",
            "integer_literal", "float_literal", "string_literal",
            "raw_string_literal", "char_literal", "boolean_literal",
            "true", "false",
        })
