"""TypeScript grammar — classes + interfaces + free functions."""
from __future__ import annotations

from typing import Any, ClassVar

from ..paradigms import MultiPurpose


class TypeScript(MultiPurpose):
    id: ClassVar[str] = "typescript"

    @classmethod
    def callable(cls) -> frozenset[str]:
        return frozenset({"function_declaration", "function_expression", "arrow_function",
                          "method_definition", "generator_function_declaration"})

    @classmethod
    def classes(cls) -> frozenset[str]:
        return frozenset({"class_declaration", "interface_declaration", "abstract_class_declaration"})

    @classmethod
    def identifiers(cls) -> frozenset[str]:
        return frozenset({"identifier", "property_identifier", "type_identifier"})

    @classmethod
    def functions(cls) -> frozenset[str]:
        return frozenset({"function_declaration", "function_expression",
                          "arrow_function", "generator_function_declaration"})

    @classmethod
    def methods(cls) -> frozenset[str]:
        return frozenset({"method_definition"})

    @classmethod
    def decision_nodes(cls) -> frozenset[str]:
        return frozenset({"if_statement", "for_statement", "for_in_statement", "for_of_statement",
                          "while_statement", "do_statement", "switch_case", "catch_clause",
                          "ternary_expression"})

    @classmethod
    def nesting_nodes(cls) -> frozenset[str]:
        return frozenset({"if_statement", "for_statement", "for_in_statement", "for_of_statement",
                          "while_statement", "do_statement", "switch_statement", "catch_clause",
                          "ternary_expression"})

    @classmethod
    def compensating_decisions(cls) -> frozenset[str]:
        return frozenset({"switch_case"})

    @classmethod
    def boolean_op_node(cls) -> str | None:
        return "binary_expression"

    @classmethod
    def boolean_op_operators(cls) -> frozenset[str] | None:
        return frozenset({"&&", "||", "??"})

    @classmethod
    def loop_nodes(cls) -> frozenset[str]:
        return frozenset({"for_statement", "for_in_statement", "for_of_statement",
                          "while_statement", "do_statement"})

    @classmethod
    def switch_nodes(cls) -> frozenset[str]:
        return frozenset({"switch_statement"})

    @classmethod
    def case_nodes(cls) -> frozenset[str]:
        return frozenset({"switch_case"})

    @classmethod
    def block_types(cls) -> frozenset[str]:
        return frozenset({"statement_block"})

    @classmethod
    def switch_body_types(cls) -> frozenset[str]:
        return frozenset({"switch_body"})

    @classmethod
    def numeric_literal_nodes(cls) -> frozenset[str]:
        return frozenset({"number"})

    @classmethod
    def operator_nodes(cls) -> frozenset[str]:
        return frozenset({
            "function", "if", "else", "for", "while", "do", "return", "class",
            "import", "from", "try", "catch", "finally", "throw", "new", "delete",
            "typeof", "instanceof", "void", "switch", "case", "default", "break",
            "continue", "var", "let", "const", "yield", "await", "async",
            "interface", "type", "enum", "as",
            "=", "+", "-", "*", "/", "%", "**", "==", "!=", "===", "!==",
            "<", ">", "<=", ">=", "&&", "||", "??", "!", "~", "&", "|", "^",
            "<<", ">>", ">>>", "+=", "-=", "*=", "/=", "%=", "**=",
            "++", "--", "=>", "...", "?",
        })

    @classmethod
    def operand_nodes(cls) -> frozenset[str]:
        return frozenset({
            "identifier", "property_identifier", "shorthand_property_identifier",
            "type_identifier", "number", "string", "string_fragment",
            "template_string", "regex", "true", "false", "null", "undefined",
        })

    @classmethod
    def import_queries(cls) -> tuple[tuple[str, str], ...]:
        return (
            ("(import_statement source: (string (string_fragment) @module))", "esm"),
            ("((call_expression function: (identifier) @fn"
             " arguments: (arguments (string (string_fragment) @module)))"
             " (#eq? @fn \"require\"))", "require"),
        )

    @classmethod
    def type_annotation_queries(cls) -> tuple[tuple[str, str], ...]:
        return (("(type_annotation (_) @annotation)", "annotation"),)

    @classmethod
    def is_escape_hatch_text(cls, text: str) -> bool:
        cleaned = text.strip().lstrip(":").strip()
        from .javascript import _type_tokens
        return cleaned == "any" or "any" in _type_tokens(cleaned)

    @classmethod
    def is_abstract_scope(cls, node: Any, content: bytes) -> bool | None:
        if node.type == "interface_declaration":
            return True
        if node.type == "abstract_class_declaration":
            return True
        if node.type == "class_declaration":
            for child in node.children:
                if child.type == "abstract":
                    return True
                if content[child.start_byte:child.end_byte].decode("utf-8", errors="replace").strip() == "abstract":
                    return True
            return False
        return None

    @classmethod
    def extract_superclasses(cls, node: Any, content: bytes) -> list[str]:
        out: list[str] = []
        for child in node.children:
            if child.type == "class_heritage":
                for clause in child.children:
                    if clause.type in ("extends_clause", "implements_clause"):
                        for c in clause.children:
                            if c.type in ("type_identifier", "identifier"):
                                out.append(content[c.start_byte:c.end_byte].decode("utf-8", errors="replace"))
        return out

    @classmethod
    def hidden_mutators(
        cls, fn_node: Any, content: bytes, *, require_type_annotation: bool = True,
    ) -> list[tuple[str, str, int]]:
        from .javascript import _js_walk_mutations, _ts_parameter_names_with_annotation
        params = _ts_parameter_names_with_annotation(fn_node, content, require_type_annotation)
        if not params:
            return []
        body = fn_node.child_by_field_name("body") or fn_node
        return _js_walk_mutations(body, content, params)
