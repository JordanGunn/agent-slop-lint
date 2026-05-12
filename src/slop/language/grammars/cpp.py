"""C++ grammar — classes + free functions + namespaces.

Overrides ``extract_name`` to handle the declarator chain
(``function_declarator → identifier``), qualified identifiers
(out-of-line methods), operator overloads, and destructors.
"""
from __future__ import annotations

from typing import Any, ClassVar

from ..multipurpose import MultiPurpose


class Cpp(MultiPurpose):
    id: ClassVar[str] = "cpp"

    @classmethod
    def callable(cls) -> frozenset[str]:
        return frozenset({"function_definition", "lambda_expression"})

    @classmethod
    def classes(cls) -> frozenset[str]:
        return frozenset({"class_specifier", "struct_specifier"})

    @classmethod
    def identifiers(cls) -> frozenset[str]:
        return frozenset({"identifier", "field_identifier", "type_identifier"})

    @classmethod
    def methods(cls) -> frozenset[str]:
        # Lambdas aren't methods.
        return frozenset({"function_definition"})

    @classmethod
    def extract_name(cls, node: Any, content: bytes) -> str:
        """Walk the C++ declarator chain to find the function name.

        Handles plain functions, pointer/reference returns, in-class
        methods, out-of-line methods (qualified_identifier), operator
        overloads, destructors.
        """
        if node.type == "lambda_expression":
            return "<lambda>"
        if node.type != "function_definition":
            # Fall back to default for non-function nodes (class_specifier etc.).
            return super().extract_name(node, content)
        declarator = node.child_by_field_name("declarator")
        for _ in range(8):
            if declarator is None:
                return "<anonymous>"
            if declarator.type == "function_declarator":
                inner = declarator.child_by_field_name("declarator")
                if inner is None:
                    return "<anonymous>"
                if inner.type in ("identifier", "field_identifier"):
                    return content[inner.start_byte:inner.end_byte].decode(
                        "utf-8", errors="replace",
                    )
                if inner.type == "qualified_identifier":
                    for c in reversed(inner.children):
                        if c.type == "identifier":
                            return content[c.start_byte:c.end_byte].decode(
                                "utf-8", errors="replace",
                            )
                    return "<anonymous>"
                if inner.type == "operator_name":
                    for c in inner.children:
                        if c.type != "operator":
                            return content[c.start_byte:c.end_byte].decode(
                                "utf-8", errors="replace",
                            ).strip()
                    return "<anonymous>"
                if inner.type == "destructor_name":
                    for c in inner.children:
                        if c.type == "identifier":
                            return "~" + content[c.start_byte:c.end_byte].decode(
                                "utf-8", errors="replace",
                            )
                    return "<anonymous>"
                return "<anonymous>"
            if declarator.type in (
                "pointer_declarator", "reference_declarator",
                "parenthesized_declarator",
            ):
                declarator = declarator.child_by_field_name("declarator")
                continue
            break
        return "<anonymous>"
