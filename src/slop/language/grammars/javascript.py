"""JavaScript grammar — classes + free functions + arrow functions.

Tree-sitter-javascript syntactically distinguishes ``function_declaration``
and ``arrow_function`` (free) from ``method_definition`` (class-bound).
"""
from __future__ import annotations

from typing import ClassVar

from ..multipurpose import MultiPurpose


class JavaScript(MultiPurpose):
    id: ClassVar[str] = "javascript"

    @classmethod
    def callable(cls) -> frozenset[str]:
        return frozenset({
            "function_declaration", "function_expression",
            "arrow_function", "method_definition",
            "generator_function_declaration",
        })

    @classmethod
    def classes(cls) -> frozenset[str]:
        return frozenset({"class_declaration"})

    @classmethod
    def identifiers(cls) -> frozenset[str]:
        return frozenset({"identifier", "property_identifier"})

    @classmethod
    def functions(cls) -> frozenset[str]:
        return frozenset({
            "function_declaration", "function_expression",
            "arrow_function", "generator_function_declaration",
        })

    @classmethod
    def methods(cls) -> frozenset[str]:
        return frozenset({"method_definition"})
