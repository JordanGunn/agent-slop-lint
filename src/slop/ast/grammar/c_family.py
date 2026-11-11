"""Facts C and C++ share: both declare switch, case, block, call and import syntax the same
way, and both read numbers, strings and boolean operators from the same node types."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..paradigm.base import ModuleIndex, c_style_parameters


class CFamily:
    @classmethod
    def compensating_decisions(cls) -> frozenset[str]:
        return frozenset({"case_statement"})

    @classmethod
    def boolean_op_node(cls) -> str | None:
        return "binary_expression"

    @classmethod
    def boolean_op_operators(cls) -> frozenset[str] | None:
        return frozenset({"&&", "||"})

    @classmethod
    def switch_nodes(cls) -> frozenset[str]:
        return frozenset({"switch_statement"})

    @classmethod
    def case_nodes(cls) -> frozenset[str]:
        return frozenset({"case_statement"})

    @classmethod
    def block_types(cls) -> frozenset[str]:
        return frozenset({"compound_statement"})

    @classmethod
    def switch_body_types(cls) -> frozenset[str]:
        return frozenset({"compound_statement"})

    @classmethod
    def numeric_literal_nodes(cls) -> frozenset[str]:
        return frozenset({"number_literal"})

    @classmethod
    def string_literal_nodes(cls) -> frozenset[str]:
        return frozenset({"raw_string_literal", "string_literal"})

    @classmethod
    def import_queries(cls) -> tuple[tuple[str, str], ...]:
        return (
            ("(preproc_include path: (string_literal (string_content) @module))", "include_local"),
            ("(preproc_include path: (system_lib_string) @module)", "include_system"),
        )

    @classmethod
    def resolve_import(cls, decl: Any, importer: Path, index: ModuleIndex) -> tuple[Any, ...]:
        """A quoted ``#include`` names a file beside the including one first, as compilers search
        it; otherwise (and for ``<...>``) the include path is unknown, so the default applies."""
        if decl.kind == "include_local":
            found = index.at(importer.parent / decl.specifier)
            if found is not None:
                return (found,)
        return super().resolve_import(decl, importer, index)

    @classmethod
    def call_node_types(cls) -> frozenset[str]:
        return frozenset({"call_expression"})

    @classmethod
    def extract_parameters(cls, node: Any, content: bytes) -> tuple[tuple[str, str | None], ...]:
        """Params hang off the function declarator; names nest in declarators."""
        return c_style_parameters(node, content)
