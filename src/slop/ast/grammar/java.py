"""Java grammar — class-only (no free functions)."""
from __future__ import annotations

from typing import Any, ClassVar

from ..paradigm import ObjectOriented
from ..paradigm.base import child_texts


class Java(ObjectOriented):
    id: ClassVar[str] = "java"

    @classmethod
    def callable(cls) -> frozenset[str]:
        return frozenset({"method_declaration", "constructor_declaration"})

    @classmethod
    def classes(cls) -> frozenset[str]:
        return frozenset({"class_declaration", "interface_declaration", "record_declaration",
                          "enum_declaration"})

    @classmethod
    def decision_nodes(cls) -> frozenset[str]:
        return frozenset({"if_statement", "for_statement", "enhanced_for_statement",
                          "while_statement", "do_statement", "switch_label", "switch_rule",
                          "catch_clause", "ternary_expression"})

    @classmethod
    def nesting_nodes(cls) -> frozenset[str]:
        return frozenset({"if_statement", "for_statement", "enhanced_for_statement",
                          "while_statement", "do_statement", "switch_statement",
                          "switch_expression", "catch_clause", "ternary_expression"})

    @classmethod
    def compensating_decisions(cls) -> frozenset[str]:
        return frozenset({"switch_label", "switch_rule"})

    @classmethod
    def boolean_op_node(cls) -> str | None:
        return "binary_expression"

    @classmethod
    def boolean_op_operators(cls) -> frozenset[str] | None:
        return frozenset({"&&", "||"})

    @classmethod
    def loop_nodes(cls) -> frozenset[str]:
        return frozenset({"for_statement", "enhanced_for_statement", "while_statement", "do_statement"})

    @classmethod
    def switch_nodes(cls) -> frozenset[str]:
        return frozenset({"switch_statement", "switch_expression"})

    @classmethod
    def case_nodes(cls) -> frozenset[str]:
        return frozenset({"switch_label", "switch_rule"})

    @classmethod
    def block_types(cls) -> frozenset[str]:
        return frozenset({"block"})

    @classmethod
    def switch_body_types(cls) -> frozenset[str]:
        return frozenset({"switch_block", "switch_block_statement_group"})

    @classmethod
    def numeric_literal_nodes(cls) -> frozenset[str]:
        return frozenset({"decimal_integer_literal", "decimal_floating_point_literal",
                          "hex_integer_literal", "octal_integer_literal"})

    @classmethod
    def string_literal_nodes(cls) -> frozenset[str]:
        return frozenset({"string_literal"})

    @classmethod
    def operator_nodes(cls) -> frozenset[str]:
        return frozenset({
            "if", "else", "for", "while", "do", "return", "class", "interface",
            "enum", "extends", "implements", "import", "package", "try", "catch",
            "finally", "throw", "throws", "new", "instanceof", "switch", "case",
            "default", "break", "continue", "public", "private", "protected",
            "static", "final", "abstract", "synchronized", "volatile", "void",
            "super", "this", "=", "+", "-", "*", "/", "%", "==", "!=", "<", ">",
            "<=", ">=", "&&", "||", "!", "~", "&", "|", "^", "<<", ">>", ">>>",
            "+=", "-=", "*=", "/=", "%=", "++", "--", "?", "->",
        })

    @classmethod
    def operand_nodes(cls) -> frozenset[str]:
        return frozenset({
            "identifier", "type_identifier", "field_identifier",
            "decimal_integer_literal", "hex_integer_literal", "octal_integer_literal",
            "binary_integer_literal", "decimal_floating_point_literal",
            "string_literal", "string_fragment", "character_literal", "true", "false", "null",
        })

    @classmethod
    def import_queries(cls) -> tuple[tuple[str, str], ...]:
        return (
            ("(import_declaration (scoped_identifier) @module)", "java_import"),
            ("(import_declaration (identifier) @module)", "java_import"),
        )

    @classmethod
    def is_abstract_scope(cls, node: Any, content: bytes) -> bool | None:
        if node.type == "interface_declaration":
            return True
        if node.type == "record_declaration":
            return False
        if node.type == "class_declaration":
            return _has_modifier(node, content, "abstract")
        return None

    @classmethod
    def extract_superclasses(cls, node: Any, content: bytes) -> list[str]:
        out: list[str] = []
        sc = node.child_by_field_name("superclass")
        if sc is not None:
            out += child_texts(sc, content, ("type_identifier",))
        ifaces = node.child_by_field_name("interfaces")
        if ifaces is not None:
            for child in ifaces.children:
                if child.type == "type_list":
                    out += child_texts(child, content, ("type_identifier",))
            out += child_texts(ifaces, content, ("type_identifier",))
        return out


def _has_modifier(node: Any, content: bytes, keyword: str) -> bool:
    for child in node.children:
        if child.type != "modifiers":
            continue
        for mod in child.children:
            if mod.type == keyword:
                return True
            if content[mod.start_byte:mod.end_byte].decode("utf-8", errors="replace").strip() == keyword:
                return True
    return False
