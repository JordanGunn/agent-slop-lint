"""C# grammar — class-only. else is a bare keyword child of if_statement."""
from __future__ import annotations

from typing import Any, ClassVar

from ..paradigm import ObjectOriented


class CSharp(ObjectOriented):
    id: ClassVar[str] = "c_sharp"

    @classmethod
    def callable(cls) -> frozenset[str]:
        return frozenset({"method_declaration", "constructor_declaration", "local_function_statement"})

    @classmethod
    def classes(cls) -> frozenset[str]:
        return frozenset({"class_declaration", "interface_declaration", "struct_declaration"})

    @classmethod
    def decision_nodes(cls) -> frozenset[str]:
        return frozenset({"if_statement", "for_statement", "foreach_statement",
                          "while_statement", "do_statement", "switch_section",
                          "catch_clause", "conditional_expression"})

    @classmethod
    def nesting_nodes(cls) -> frozenset[str]:
        return frozenset({"if_statement", "for_statement", "foreach_statement",
                          "while_statement", "do_statement", "switch_statement",
                          "catch_clause", "conditional_expression"})

    @classmethod
    def compensating_decisions(cls) -> frozenset[str]:
        return frozenset({"switch_section"})

    @classmethod
    def boolean_op_node(cls) -> str | None:
        return "binary_expression"

    @classmethod
    def boolean_op_operators(cls) -> frozenset[str] | None:
        return frozenset({"&&", "||"})

    @classmethod
    def else_nodes(cls) -> frozenset[str]:
        return frozenset()  # C# emits bare 'else' keyword

    @classmethod
    def bare_else_keyword(cls) -> str | None:
        return "else"

    @classmethod
    def loop_nodes(cls) -> frozenset[str]:
        return frozenset({"for_statement", "foreach_statement", "while_statement", "do_statement"})

    @classmethod
    def switch_nodes(cls) -> frozenset[str]:
        return frozenset({"switch_statement"})

    @classmethod
    def case_nodes(cls) -> frozenset[str]:
        return frozenset({"switch_section"})

    @classmethod
    def block_types(cls) -> frozenset[str]:
        return frozenset({"block"})

    @classmethod
    def switch_body_types(cls) -> frozenset[str]:
        return frozenset({"switch_body"})

    @classmethod
    def numeric_literal_nodes(cls) -> frozenset[str]:
        return frozenset({"integer_literal", "real_literal"})

    @classmethod
    def operator_nodes(cls) -> frozenset[str]:
        return frozenset({
            "if", "else", "for", "foreach", "while", "do", "return", "class",
            "struct", "interface", "enum", "using", "namespace", "try", "catch",
            "finally", "throw", "new", "is", "as", "switch", "in", "case",
            "default", "break", "continue", "public", "private", "protected",
            "internal", "static", "readonly", "abstract", "virtual", "override",
            "sealed", "async", "await", "void", "this", "base", "var",
            "=", "+", "-", "*", "/", "%", "==", "!=", "<", ">", "<=", ">=",
            "&&", "||", "!", "~", "&", "|", "^", "<<", ">>",
            "+=", "-=", "*=", "/=", "%=", "++", "--", "?", "=>", "??",
        })

    @classmethod
    def operand_nodes(cls) -> frozenset[str]:
        return frozenset({
            "identifier", "type_identifier", "integer_literal", "real_literal",
            "string_literal", "verbatim_string_literal", "interpolated_string_expression",
            "character_literal", "true", "false", "null",
        })

    @classmethod
    def import_queries(cls) -> tuple[tuple[str, str], ...]:
        return (
            ("(using_directive (identifier) @module)", "csharp_using"),
            ("(using_directive (qualified_name) @module)", "csharp_using"),
        )

    @classmethod
    def type_annotation_queries(cls) -> tuple[tuple[str, str], ...]:
        return (
            ("(parameter type: (_) @annotation)", "param"),
            ("(method_declaration returns: (_) @annotation)", "return"),
        )

    @classmethod
    def is_dynamic_type(cls, text: str) -> bool:
        cleaned = text.strip()
        if cleaned in ("object", "dynamic"):
            return True
        toks = _word_tokens(cleaned)
        return "object" in toks or "dynamic" in toks

    @classmethod
    def is_abstract_scope(cls, node: Any, content: bytes) -> bool | None:
        if node.type == "interface_declaration":
            return True
        if node.type == "struct_declaration":
            return False
        if node.type == "class_declaration":
            for child in node.children:
                if child.type == "modifier":
                    if content[child.start_byte:child.end_byte].decode("utf-8", errors="replace").strip() == "abstract":
                        return True
            return False
        return None

    @classmethod
    def extract_superclasses(cls, node: Any, content: bytes) -> list[str]:
        out: list[str] = []
        for child in node.children:
            if child.type == "base_list":
                for gc in child.children:
                    if gc.type == "identifier":
                        out.append(content[gc.start_byte:gc.end_byte].decode("utf-8", errors="replace"))
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
