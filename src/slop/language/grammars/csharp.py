"""C# grammar — class-only (no top-level free functions historically)."""
from __future__ import annotations

from typing import ClassVar

from ..objectoriented import ObjectOriented


class CSharp(ObjectOriented):
    id: ClassVar[str] = "c_sharp"

    @classmethod
    def callable(cls) -> frozenset[str]:
        return frozenset({
            "method_declaration", "constructor_declaration",
            "local_function_statement",
        })

    @classmethod
    def classes(cls) -> frozenset[str]:
        return frozenset({"class_declaration", "interface_declaration", "struct_declaration"})
