"""Java grammar — class-only (no free functions)."""
from __future__ import annotations

from typing import Any, ClassVar

from ..paradigm import ObjectOriented


class Java(ObjectOriented):
    id: ClassVar[str] = "java"

    @classmethod
    def callable(cls) -> frozenset[str]:
        return frozenset({"method_declaration", "constructor_declaration"})

    @classmethod
    def classes(cls) -> frozenset[str]:
        return frozenset({"class_declaration", "interface_declaration", "record_declaration"})

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
    def type_annotation_queries(cls) -> tuple[tuple[str, str], ...]:
        return (
            ("(formal_parameter type: (_) @annotation)", "param"),
            ("(method_declaration type: (_) @annotation)", "return"),
        )

    @classmethod
    def is_dynamic_type(cls, text: str) -> bool:
        cleaned = text.strip()
        if cleaned == "Object":
            return True
        return "Object" in _word_tokens(cleaned)

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
            for child in sc.children:
                if child.type == "type_identifier":
                    out.append(content[child.start_byte:child.end_byte].decode("utf-8", errors="replace"))
        ifaces = node.child_by_field_name("interfaces")
        if ifaces is not None:
            for child in ifaces.children:
                if child.type == "type_list":
                    for tc in child.children:
                        if tc.type == "type_identifier":
                            out.append(content[tc.start_byte:tc.end_byte].decode("utf-8", errors="replace"))
                elif child.type == "type_identifier":
                    out.append(content[child.start_byte:child.end_byte].decode("utf-8", errors="replace"))
        return out


def _word_tokens(text: str) -> set[str]:
    tokens: set[str] = set()
    buf: list[str] = []
    for ch in text:
        if ch.isalnum() or ch == "_":
            buf.append(ch)
        elif buf:
            tokens.add("".join(buf)); buf = []
    if buf:
        tokens.add("".join(buf))
    return tokens


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
