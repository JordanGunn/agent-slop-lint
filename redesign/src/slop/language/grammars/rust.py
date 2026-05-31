"""Rust grammar — struct/enum/trait + impl blocks + free functions.

impl_item is NOT a type, so it is excluded from classes(); its function_items are
carved at module level and reparented to the impl's target type via
reparent_callable (parent-walk to the enclosing impl_item) — replacing the legacy
post_scan_adjust. Inheritance-shaped metrics are absent (extract_superclasses
defaults to []). Also fixes a legacy bug (operator/operand_nodes were dead code
nested in a helper).
"""
from __future__ import annotations

from typing import Any, ClassVar

from ..paradigms import MultiPurpose


class Rust(MultiPurpose):
    id: ClassVar[str] = "rust"

    @classmethod
    def callable(cls) -> frozenset[str]:
        return frozenset({"function_item"})

    @classmethod
    def classes(cls) -> frozenset[str]:
        # impl_item is deliberately excluded — it is a method-grouping block, not
        # a type. Its methods reparent to the target struct/enum/trait.
        return frozenset({"struct_item", "enum_item", "trait_item"})

    @classmethod
    def identifiers(cls) -> frozenset[str]:
        return frozenset({"identifier", "field_identifier", "type_identifier"})

    @classmethod
    def decision_nodes(cls) -> frozenset[str]:
        return frozenset({"if_expression", "while_expression", "for_expression", "match_arm"})

    @classmethod
    def nesting_nodes(cls) -> frozenset[str]:
        return frozenset({"if_expression", "while_expression", "for_expression", "match_expression"})

    @classmethod
    def compensating_decisions(cls) -> frozenset[str]:
        return frozenset({"match_arm"})

    @classmethod
    def boolean_op_node(cls) -> str | None:
        return "binary_expression"

    @classmethod
    def boolean_op_operators(cls) -> frozenset[str] | None:
        return frozenset({"&&", "||"})

    @classmethod
    def if_nodes(cls) -> frozenset[str]:
        return frozenset({"if_expression"})

    @classmethod
    def try_nodes(cls) -> frozenset[str]:
        return frozenset()

    @classmethod
    def catch_nodes(cls) -> frozenset[str]:
        return frozenset()

    @classmethod
    def loop_nodes(cls) -> frozenset[str]:
        return frozenset({"for_expression", "while_expression", "loop_expression"})

    @classmethod
    def switch_nodes(cls) -> frozenset[str]:
        return frozenset({"match_expression"})

    @classmethod
    def case_nodes(cls) -> frozenset[str]:
        return frozenset({"match_arm"})

    @classmethod
    def block_types(cls) -> frozenset[str]:
        return frozenset({"block"})

    @classmethod
    def numeric_literal_nodes(cls) -> frozenset[str]:
        return frozenset({"integer_literal", "float_literal"})

    @classmethod
    def operator_nodes(cls) -> frozenset[str]:
        return frozenset({
            "fn", "if", "else", "for", "while", "loop", "match", "return",
            "break", "continue", "let", "mut", "ref", "struct", "enum", "impl",
            "trait", "type", "use", "mod", "pub", "self", "super", "crate", "as",
            "where", "async", "await", "unsafe", "move",
            "=", "+", "-", "*", "/", "%", "==", "!=", "<", ">", "<=", ">=",
            "&&", "||", "!", "&", "|", "^", "<<", ">>",
            "+=", "-=", "*=", "/=", "%=", "=>", "::", "..", "..=", "?",
        })

    @classmethod
    def operand_nodes(cls) -> frozenset[str]:
        return frozenset({
            "identifier", "field_identifier", "type_identifier", "integer_literal",
            "float_literal", "string_literal", "raw_string_literal", "char_literal",
            "boolean_literal", "true", "false",
        })

    @classmethod
    def import_queries(cls) -> tuple[tuple[str, str], ...]:
        return (
            ("(use_declaration argument: (scoped_identifier) @module)", "use"),
            ("(use_declaration argument: (identifier) @module)", "use"),
            ("(use_declaration argument: (use_as_clause path: (scoped_identifier) @module))", "use"),
            ("(use_declaration argument: (use_as_clause path: (identifier) @module))", "use"),
            ("(use_declaration argument: (scoped_use_list path: (scoped_identifier) @module))", "use"),
            ("(use_declaration argument: (scoped_use_list path: (identifier) @module))", "use"),
        )

    @classmethod
    def type_annotation_queries(cls) -> tuple[tuple[str, str], ...]:
        return (
            ("(parameter type: (_) @annotation)", "param"),
            ("(function_item return_type: (_) @annotation)", "return"),
        )

    @classmethod
    def is_escape_hatch_text(cls, text: str) -> bool:
        return "dyn Any" in text or "dyn std::any::Any" in text

    @classmethod
    def is_abstract_scope(cls, node: Any, content: bytes) -> bool | None:
        del content
        if node.type == "trait_item":
            return True
        if node.type in ("struct_item", "enum_item"):
            return False
        return None

    @classmethod
    def reparent_callable(cls, node: Any, content: bytes) -> str | None:
        if node.type != "function_item":
            return None
        cur = node.parent
        while cur is not None:
            if cur.type == "impl_item":
                type_node = cur.child_by_field_name("type")
                return _rust_target_type_name(type_node, content) if type_node is not None else None
            cur = cur.parent
        return None


def _rust_target_type_name(type_node: Any, content: bytes) -> str | None:
    if type_node.type == "type_identifier":
        return content[type_node.start_byte:type_node.end_byte].decode("utf-8", errors="replace")
    if type_node.type == "generic_type":
        for child in type_node.children:
            if child.type == "type_identifier":
                return content[child.start_byte:child.end_byte].decode("utf-8", errors="replace")
    return None
