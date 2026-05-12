"""TypeScript grammar — classes + interfaces + free functions.

Like JavaScript, syntactically distinguishes function/method node types.
"""
from __future__ import annotations

from typing import ClassVar

from ..multipurpose import MultiPurpose


class TypeScript(MultiPurpose):
    id: ClassVar[str] = "typescript"

    @classmethod
    def callable(cls) -> frozenset[str]:
        return frozenset({
            "function_declaration", "function_expression",
            "arrow_function", "method_definition",
            "generator_function_declaration",
        })

    @classmethod
    def classes(cls) -> frozenset[str]:
        return frozenset({"class_declaration", "interface_declaration"})

    @classmethod
    def identifiers(cls) -> frozenset[str]:
        return frozenset({"identifier", "property_identifier", "type_identifier"})

    @classmethod
    def functions(cls) -> frozenset[str]:
        return frozenset({
            "function_declaration", "function_expression",
            "arrow_function", "generator_function_declaration",
        })

    @classmethod
    def methods(cls) -> frozenset[str]:
        return frozenset({"method_definition"})
