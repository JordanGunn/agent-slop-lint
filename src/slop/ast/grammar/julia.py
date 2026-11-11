"""Julia grammar — struct/abstract/primitive type definitions are class-like scopes (methods
live outside them, by multiple dispatch); flat-body. extract_name walks signature→call."""
from __future__ import annotations

from typing import Any, ClassVar

from ..paradigm import MultiPurpose
from ..paradigm.base import julia_signature_parameters
from ..paradigm.heritage import type_name


class Julia(MultiPurpose):
    id: ClassVar[str] = "julia"

    @classmethod
    def classes(cls) -> frozenset[str]:
        return frozenset({"struct_definition", "abstract_definition", "primitive_definition"})

    @classmethod
    def methods(cls) -> frozenset[str]:
        return frozenset()

    @classmethod
    def callable(cls) -> frozenset[str]:
        return frozenset({"function_definition", "arrow_function_expression"})

    @classmethod
    def decision_nodes(cls) -> frozenset[str]:
        return frozenset({"if_statement", "elseif_clause", "for_statement",
                          "while_statement", "catch_clause", "ternary_expression"})

    @classmethod
    def nesting_nodes(cls) -> frozenset[str]:
        return frozenset({"if_statement", "for_statement", "while_statement",
                          "try_statement", "catch_clause", "ternary_expression"})

    @classmethod
    def compensating_decisions(cls) -> frozenset[str]:
        return frozenset({"elseif_clause"})

    @classmethod
    def boolean_op_node(cls) -> str | None:
        return "binary_expression"

    @classmethod
    def boolean_op_operators(cls) -> frozenset[str] | None:
        return frozenset({"&&", "||"})

    @classmethod
    def elif_nodes(cls) -> frozenset[str]:
        return frozenset({"elseif_clause"})

    @classmethod
    def loop_nodes(cls) -> frozenset[str]:
        return frozenset({"for_statement", "while_statement"})

    @classmethod
    def body_field(cls) -> str:
        return ""  # flat-body: statements are direct children

    @classmethod
    def body_skip_types(cls) -> frozenset[str]:
        return frozenset({"function", "end", "signature", "if", "elseif", "else",
                          "for", "for_binding", "while", "try", "catch", "finally", "do"})

    @classmethod
    def numeric_literal_nodes(cls) -> frozenset[str]:
        return frozenset({"integer_literal", "float_literal"})

    @classmethod
    def string_literal_nodes(cls) -> frozenset[str]:
        return frozenset({"string_literal"})

    @classmethod
    def operator_nodes(cls) -> frozenset[str]:
        return frozenset({
            "function", "return", "if", "else", "elseif", "end", "for", "while",
            "break", "continue", "in", "try", "catch", "finally", "throw", "do",
            "begin", "let", "global", "local", "module", "using", "import", "export",
            "struct", "mutable", "abstract", "primitive", "type", "const",
            "operator",     # the node type of every infix operator token; its text is the symbol
            "=", "+", "-", "*", "/", "%", "^", "//", ".",
            "==", "!=", "<", ">", "<=", ">=", "===", "!==",
            "&&", "||", "!", "&", "|", "<<", ">>", "+=", "-=", "*=", "/=",
            "->", "::", ":", "?", "@", "...",
        })

    @classmethod
    def operand_nodes(cls) -> frozenset[str]:
        return frozenset({"identifier", "integer_literal", "float_literal",
                          "string_literal", "character_literal", "true", "false", "nothing", "missing"})

    @classmethod
    def import_queries(cls) -> tuple[tuple[str, str], ...]:
        return (
            ("(using_statement (identifier) @module)", "julia_using"),
            ("(using_statement (scoped_identifier) @module)", "julia_using"),
            ("(using_statement (selected_import . (identifier) @module))", "julia_using"),
            ("(import_statement (identifier) @module)", "julia_import"),
            ("(import_statement (scoped_identifier) @module)", "julia_import"),
            ("(import_statement (selected_import . (identifier) @module))", "julia_import"),
        )

    @classmethod
    def extract_name(cls, node: Any, content: bytes) -> str:
        if node.type in cls.classes():
            ident = _head_identifier(node)
            return _text(ident, content) if ident is not None else "<anonymous>"
        if node.type == "arrow_function_expression":
            return "<lambda>"
        if node.type != "function_definition":
            return super().extract_name(node, content)
        signature = next((c for c in node.children if c.type == "signature"), None)
        if signature is None:
            return "<anonymous>"
        call_expr = next((c for c in signature.children if c.type == "call_expression"), None)
        if call_expr is None:
            return "<anonymous>"
        ident = next((c for c in call_expr.children if c.type == "identifier"), None)
        if ident is None:
            return "<anonymous>"
        return content[ident.start_byte:ident.end_byte].decode("utf-8", errors="replace")

    @classmethod
    def extract_parameters(cls, node: Any, content: bytes) -> tuple[tuple[str, str | None], ...]:
        """Julia params live under ``signature → call_expression → argument_list``."""
        return julia_signature_parameters(node, content)

    @classmethod
    def is_abstract_scope(cls, node: Any, content: bytes) -> bool | None:
        del content
        return True if node.type == "abstract_definition" else None

    @classmethod
    def extract_superclasses(cls, node: Any, content: bytes) -> list[str]:
        """``struct Circle <: Shape`` extends ``Shape``."""
        head = next((c for c in node.children if c.type == "type_head"), None)
        if head is None or not head.children or head.children[0].type != "binary_expression":
            return []
        supertype = type_name(head.children[0].children[-1], content)
        return [supertype] if supertype is not None else []


def _leftmost_identifier(node: Any) -> Any | None:
    """The first identifier reached by descending first children (``Box{T}`` -> ``Box``)."""
    while node is not None and node.type != "identifier":
        node = node.children[0] if node.children else None
    return node


def _head_identifier(node: Any) -> Any | None:
    """The declared name of a struct/abstract/primitive definition: the leftmost
    identifier of its ``type_head`` (past ``<:`` and type parameters)."""
    head = next((c for c in node.children if c.type == "type_head"), None)
    return _leftmost_identifier(head)


def _text(node: Any, content: bytes) -> str:
    return content[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
