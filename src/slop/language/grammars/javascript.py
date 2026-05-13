"""JavaScript grammar — classes + free functions + arrow functions.

Tree-sitter-javascript syntactically distinguishes ``function_declaration``
and ``arrow_function`` (free) from ``method_definition`` (class-bound).
"""
from __future__ import annotations

from typing import Any, ClassVar

from ..ast import Block, Callable, Catch, Conditional, Identifier, Literal, Loop, Operator, Scope, Switch
from ..multipurpose import MultiPurpose


class JavaScript(MultiPurpose):
    id: ClassVar[str] = "javascript"

    @classmethod
    def callable(cls) -> frozenset[str]:
        return frozenset({
            Callable.FUNCTION_DECLARATION, Callable.FUNCTION_EXPRESSION,
            Callable.ARROW_FUNCTION, Callable.METHOD_DEFINITION,
            Callable.GENERATOR_FUNCTION_DECLARATION,
        })

    @classmethod
    def classes(cls) -> frozenset[str]:
        return frozenset({Scope.CLASS_DECLARATION})

    @classmethod
    def identifiers(cls) -> frozenset[str]:
        return frozenset({Identifier.IDENTIFIER, Identifier.PROPERTY_IDENTIFIER})

    @classmethod
    def functions(cls) -> frozenset[str]:
        return frozenset({
            Callable.FUNCTION_DECLARATION, Callable.FUNCTION_EXPRESSION,
            Callable.ARROW_FUNCTION, Callable.GENERATOR_FUNCTION_DECLARATION,
        })

    @classmethod
    def methods(cls) -> frozenset[str]:
        return frozenset({Callable.METHOD_DEFINITION})

    @classmethod
    def decision_nodes(cls) -> frozenset[str]:
        return frozenset({
            Conditional.IF_STATEMENT,
            Loop.FOR_STATEMENT, Loop.FOR_IN_STATEMENT, Loop.FOR_OF_STATEMENT,
            Loop.WHILE_STATEMENT, Loop.DO_STATEMENT,
            Switch.SWITCH_CASE,
            Catch.CATCH_CLAUSE,
            Conditional.TERNARY_EXPRESSION,
        })

    @classmethod
    def nesting_nodes(cls) -> frozenset[str]:
        return frozenset({
            Conditional.IF_STATEMENT,
            Loop.FOR_STATEMENT, Loop.FOR_IN_STATEMENT, Loop.FOR_OF_STATEMENT,
            Loop.WHILE_STATEMENT, Loop.DO_STATEMENT,
            Switch.SWITCH_STATEMENT,                # container for switch_case
            Catch.CATCH_CLAUSE,
            Conditional.TERNARY_EXPRESSION,
        })

    @classmethod
    def compensating_decisions(cls) -> frozenset[str]:
        return frozenset({Switch.SWITCH_CASE})

    @classmethod
    def boolean_op_node(cls) -> str | None:
        return Operator.BINARY_EXPRESSION

    @classmethod
    def boolean_op_operators(cls) -> frozenset[str] | None:
        return frozenset({"&&", "||", "??"})

    @classmethod
    def if_nodes(cls) -> frozenset[str]:
        return frozenset({Conditional.IF_STATEMENT})

    @classmethod
    def else_nodes(cls) -> frozenset[str]:
        return frozenset({Conditional.ELSE_CLAUSE})

    @classmethod
    def loop_nodes(cls) -> frozenset[str]:
        return frozenset({
            Loop.FOR_STATEMENT, Loop.FOR_IN_STATEMENT, Loop.FOR_OF_STATEMENT,
            Loop.WHILE_STATEMENT, Loop.DO_STATEMENT,
        })

    @classmethod
    def switch_nodes(cls) -> frozenset[str]:
        return frozenset({Switch.SWITCH_STATEMENT})

    @classmethod
    def case_nodes(cls) -> frozenset[str]:
        return frozenset({Switch.SWITCH_CASE})

    @classmethod
    def try_nodes(cls) -> frozenset[str]:
        return frozenset({Catch.TRY_STATEMENT})

    @classmethod
    def catch_nodes(cls) -> frozenset[str]:
        return frozenset({Catch.CATCH_CLAUSE})

    @classmethod
    def block_types(cls) -> frozenset[str]:
        return frozenset({Block.STATEMENT_BLOCK})

    @classmethod
    def switch_body_types(cls) -> frozenset[str]:
        return frozenset({Block.SWITCH_BODY})

    @classmethod
    def numeric_literal_nodes(cls) -> frozenset[str]:
        return frozenset({Literal.NUMBER})

    @classmethod
    def operator_nodes(cls) -> frozenset[str]:
        return frozenset({
            "function", "if", "else", "for", "while", "do", "return",
            "class", "import", "from", "try", "catch", "finally",
            "throw", "new", "delete", "typeof", "instanceof", "void",
            "switch", "case", "default", "break", "continue",
            "var", "let", "const", "yield", "await", "async",
            "=", "+", "-", "*", "/", "%", "**",
            "==", "!=", "===", "!==", "<", ">", "<=", ">=",
            "&&", "||", "??", "!", "~", "&", "|", "^", "<<", ">>", ">>>",
            "+=", "-=", "*=", "/=", "%=", "**=",
            "++", "--", "=>", "...", "?",
        })

    @classmethod
    def operand_nodes(cls) -> frozenset[str]:
        return frozenset({
            "identifier", "property_identifier", "shorthand_property_identifier",
            "number", "string", "string_fragment",
            "template_string", "regex",
            "true", "false", "null", "undefined",
        })

    @classmethod
    def extract_superclasses(cls, node: Any, content: bytes) -> list[str]:
        """JS: ``class Foo extends Bar`` — class_heritage with bare identifier."""
        out: list[str] = []
        for child in node.children:
            if child.type == "class_heritage":
                for c in child.children:
                    if c.type == "identifier":
                        out.append(content[c.start_byte:c.end_byte].decode("utf-8", errors="replace"))
        return out
