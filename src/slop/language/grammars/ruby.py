"""Ruby grammar — classes + modules + methods.

Tree-sitter-ruby uses ``method`` and ``singleton_method`` node types,
positional naming (no ``name`` field). Overrides ``extract_name`` to
skip ``def``/``self``/``.`` tokens.
"""
from __future__ import annotations

from typing import Any, ClassVar

from ..ast import Callable as Node
from ..ast import Block, Catch, Conditional, Identifier, Literal, Loop, Operator, Scope, Switch
from ..multipurpose import MultiPurpose


class Ruby(MultiPurpose):
    id: ClassVar[str] = "ruby"

    @classmethod
    def callable(cls) -> frozenset[str]:
        return frozenset({Node.METHOD, Node.SINGLETON_METHOD})

    @classmethod
    def classes(cls) -> frozenset[str]:
        return frozenset({Scope.CLASS, Scope.MODULE})

    @classmethod
    def decision_nodes(cls) -> frozenset[str]:
        return frozenset({
            Conditional.IF, Conditional.ELSIF,
            Conditional.UNLESS_MODIFIER, Conditional.IF_MODIFIER,
            Loop.WHILE_MODIFIER, Loop.UNTIL_MODIFIER,
            Catch.RESCUE_MODIFIER,
            Loop.WHILE, Loop.UNTIL, Loop.FOR,
            Switch.WHEN,
            Catch.RESCUE,
            Conditional.CONDITIONAL,                # ternary x ? a : b
        })

    @classmethod
    def nesting_nodes(cls) -> frozenset[str]:
        return frozenset({
            Conditional.IF, Conditional.UNLESS_MODIFIER,
            Loop.WHILE, Loop.UNTIL, Loop.FOR,
            Switch.CASE, Catch.BEGIN,
            Conditional.CONDITIONAL,
            Node.DO_BLOCK, Node.BLOCK,
        })

    @classmethod
    def compensating_decisions(cls) -> frozenset[str]:
        return frozenset({
            Conditional.ELSIF,                      # syntactically inside if
            Switch.WHEN,                            # syntactically inside case
        })

    @classmethod
    def boolean_op_node(cls) -> str | None:
        return Operator.BINARY

    @classmethod
    def boolean_op_operators(cls) -> frozenset[str] | None:
        return frozenset({"&&", "||", "and", "or"})

    @classmethod
    def if_nodes(cls) -> frozenset[str]:
        return frozenset({Conditional.IF})

    @classmethod
    def elif_nodes(cls) -> frozenset[str]:
        return frozenset({Conditional.ELSIF})

    @classmethod
    def else_nodes(cls) -> frozenset[str]:
        return frozenset({Conditional.ELSE})

    @classmethod
    def loop_nodes(cls) -> frozenset[str]:
        return frozenset({Loop.WHILE, Loop.UNTIL, Loop.FOR})

    @classmethod
    def switch_nodes(cls) -> frozenset[str]:
        return frozenset({Switch.CASE})

    @classmethod
    def case_nodes(cls) -> frozenset[str]:
        return frozenset({Switch.WHEN})

    @classmethod
    def try_nodes(cls) -> frozenset[str]:
        return frozenset({Catch.BEGIN})

    @classmethod
    def catch_nodes(cls) -> frozenset[str]:
        return frozenset({Catch.RESCUE})

    @classmethod
    def body_field(cls) -> str:
        # Flat-body language: method bodies are positional inside
        # body_statement, not behind a 'body' field.
        return ""

    @classmethod
    def block_types(cls) -> frozenset[str]:
        return frozenset({Block.BODY_STATEMENT})

    @classmethod
    def body_skip_types(cls) -> frozenset[str]:
        return frozenset({
            "def", "end", "do", "then",
            "identifier", "operator",
            "method_parameters", "block_parameters", "lambda_parameters",
            "self", ".",
            "class", "module", "constant", "superclass",
            "if", "elsif", "else", "case", "when",
            "while", "until", "for", "in",
            "begin", "rescue", "ensure", "exceptions", "exception_variable",
        })

    @classmethod
    def numeric_literal_nodes(cls) -> frozenset[str]:
        return frozenset({
            Literal.INTEGER, Literal.FLOAT,
            Literal.COMPLEX, Literal.RATIONAL,
        })

    @classmethod
    def extract_superclasses(cls, node: Any, content: bytes) -> list[str]:
        """Ruby: ``class Dog < Animal`` — superclass child.

        Modules have no superclass concept. Mixins (``include MyMod``)
        are body call-statements and are NOT counted as inheritance for
        DIT — Ruby convention treats them as composition (the CBO
        metric captures the coupling).
        """
        if node.type == "module":
            return []
        for child in node.children:
            if child.type == "superclass":
                for sub in child.children:
                    if sub.type == "constant":
                        return [content[sub.start_byte:sub.end_byte].decode("utf-8", errors="replace")]
        return []

    @classmethod
    def operator_nodes(cls) -> frozenset[str]:
        return frozenset({
            # Keywords
            "def", "end", "class", "module",
            "if", "elsif", "else", "unless",
            "while", "until", "for", "in",
            "case", "when", "then", "do",
            "return", "yield", "break", "next", "redo", "retry",
            "begin", "rescue", "ensure", "raise",
            "require", "require_relative", "load",
            "include", "extend", "prepend",
            "public", "private", "protected",
            "attr_reader", "attr_writer", "attr_accessor",
            "lambda", "proc", "super",
            "self", "nil", "true", "false",
            "not", "and", "or",
            "=", "+", "-", "*", "/", "%", "**",
            "==", "===", "!=", "<", ">", "<=", ">=", "<=>",
            "&&", "||", "!",
            "&", "|", "^", "~", "<<", ">>",
            "+=", "-=", "*=", "/=", "%=", "**=",
            "&&=", "||=",
            "..", "...",
            "=>", "->",
            "?", ":", ",", ".", "::",
        })

    @classmethod
    def operand_nodes(cls) -> frozenset[str]:
        return frozenset({
            "identifier",
            "instance_variable", "class_variable", "global_variable",
            "constant",
            "integer", "float", "complex", "rational",
            "string", "string_content",
            "symbol", "simple_symbol", "hash_key_symbol",
            "true", "false", "nil",
        })

    @classmethod
    def extract_name(cls, node: Any, content: bytes) -> str:
        """Walk method / singleton_method children, skipping def/self/."""
        if node.type not in (Node.METHOD, Node.SINGLETON_METHOD):
            return super().extract_name(node, content)
        saw_def = False
        saw_self = False
        saw_dot = False
        for child in node.children:
            ctype = child.type
            if ctype == "def":
                saw_def = True
                continue
            if not saw_def:
                continue
            if ctype == "self" and not saw_self:
                saw_self = True
                continue
            if ctype == "." and saw_self and not saw_dot:
                saw_dot = True
                continue
            if ctype in (Identifier.IDENTIFIER, Identifier.OPERATOR):
                return content[child.start_byte:child.end_byte].decode(
                    "utf-8", errors="replace",
                ).strip()
        return "<anonymous>"
