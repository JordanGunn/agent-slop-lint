"""Tests for the C concrete grammar — declarator-chain extract_name quirk."""
from __future__ import annotations

from pathlib import Path

from slop._ast.treesitter import parse_file
from slop.language.grammars import C


class TestCExtraction:
    def test_id_is_c(self):
        assert C.id == "c"

    def test_callable_is_function_definition(self):
        assert C.callable() == frozenset({"function_definition"})

    def test_extract_name_walks_declarator_chain(self, tmp_path: Path):
        src = tmp_path / "x.c"
        src.write_text("int my_func(int x) { return x; }\n")
        parsed = parse_file(src, "c")
        assert parsed is not None
        tree, content = parsed
        # Find the function_definition node and run the C extract_name.
        for child in tree.root_node.children:
            if child.type == "function_definition":
                assert C.extract_name(child, content) == "my_func"
                return
        raise AssertionError("function_definition not found")
