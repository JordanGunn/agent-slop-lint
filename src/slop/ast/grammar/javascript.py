"""JavaScript grammar — classes + free functions + arrow functions."""
from __future__ import annotations

from typing import Any, ClassVar

from ..paradigm import MultiPurpose
from ..paradigm.base import child_texts
from .ecmascript import EcmaScript


class JavaScript(EcmaScript, MultiPurpose):
    id: ClassVar[str] = "javascript"

    @classmethod
    def classes(cls) -> frozenset[str]:
        return frozenset({"class_declaration"})

    @classmethod
    def identifiers(cls) -> frozenset[str]:
        return frozenset({"identifier", "property_identifier"})

    @classmethod
    def methods(cls) -> frozenset[str]:
        return frozenset({"method_definition"})

    @classmethod
    def compensating_decisions(cls) -> frozenset[str]:
        return frozenset({"switch_case"})

    @classmethod
    def boolean_op_node(cls) -> str | None:
        return "binary_expression"

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
    def string_literal_nodes(cls) -> frozenset[str]:
        return frozenset({"string"})

    @classmethod
    def operator_nodes(cls) -> frozenset[str]:
        return frozenset({
            "function", "if", "else", "for", "while", "do", "return", "class",
            "import", "from", "try", "catch", "finally", "throw", "new", "delete",
            "typeof", "instanceof", "void", "switch", "case", "default", "break",
            "continue", "var", "let", "const", "yield", "await", "async",
            "=", "+", "-", "*", "/", "%", "**", "==", "!=", "===", "!==",
            "<", ">", "<=", ">=", "&&", "||", "??", "!", "~", "&", "|", "^",
            "<<", ">>", ">>>", "+=", "-=", "*=", "/=", "%=", "**=",
            "++", "--", "=>", "...", "?",
        })

    @classmethod
    def operand_nodes(cls) -> frozenset[str]:
        return frozenset({
            "identifier", "property_identifier", "shorthand_property_identifier",
            "number", "string", "string_fragment", "template_string", "regex",
            "true", "false", "null", "undefined",
        })

    @classmethod
    def is_abstract_scope(cls, node: Any, content: bytes) -> bool | None:
        del content
        return False if node.type == "class_declaration" else None

    @classmethod
    def extract_superclasses(cls, node: Any, content: bytes) -> list[str]:
        return [name for child in node.children if child.type == "class_heritage"
                for name in child_texts(child, content, ("identifier",))]
