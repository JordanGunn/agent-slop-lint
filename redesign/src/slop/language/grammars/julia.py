"""Julia grammar — procedural; flat-body. extract_name walks signature→call."""
from __future__ import annotations

from typing import Any, ClassVar

from ..paradigms import Procedural


class Julia(Procedural):
    id: ClassVar[str] = "julia"

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
    def operator_nodes(cls) -> frozenset[str]:
        return frozenset({
            "function", "return", "if", "else", "elseif", "end", "for", "while",
            "break", "continue", "in", "try", "catch", "finally", "throw", "do",
            "begin", "let", "global", "local", "module", "using", "import", "export",
            "struct", "mutable", "abstract", "primitive", "type", "const",
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
    def type_annotation_queries(cls) -> tuple[tuple[str, str], ...]:
        return (("(typed_expression . (_) (_) @annotation)", "annotation"),)

    @classmethod
    def is_escape_hatch_text(cls, text: str) -> bool:
        cleaned = text.strip().lstrip(":").strip()
        return cleaned == "Any" or cleaned.endswith(".Any")

    @classmethod
    def extract_name(cls, node: Any, content: bytes) -> str:
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
