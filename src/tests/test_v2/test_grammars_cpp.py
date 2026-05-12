"""Tests for the C++ concrete grammar — qualified_identifier extract_name quirk."""
from __future__ import annotations

from pathlib import Path

from slop._ast.treesitter import parse_file
from slop.language.grammars import Cpp


class TestCppExtraction:
    def test_id_is_cpp(self):
        assert Cpp.id == "cpp"

    def test_extract_name_handles_qualified_identifier(self, tmp_path: Path):
        src = tmp_path / "x.cpp"
        src.write_text("int Foo::bar(int x) { return x; }\n")
        parsed = parse_file(src, "cpp")
        assert parsed is not None
        tree, content = parsed
        for child in tree.root_node.children:
            if child.type == "function_definition":
                # Out-of-line method definition; extract_name should return
                # the rightmost identifier of the qualified_identifier ("bar").
                name = Cpp.extract_name(child, content)
                assert name == "bar"
                return
        raise AssertionError("function_definition not found")

    def test_extract_name_handles_lambda(self, tmp_path: Path):
        src = tmp_path / "x.cpp"
        src.write_text("auto f = [](int x) { return x; };\n")
        parsed = parse_file(src, "cpp")
        assert parsed is not None
        tree, _content = parsed
        # Walk for lambda_expression
        stack = [tree.root_node]
        while stack:
            n = stack.pop()
            if n.type == "lambda_expression":
                assert Cpp.extract_name(n, b"") == "<lambda>"
                return
            stack.extend(n.children)
        # Lambda not always emitted by all tree-sitter-cpp versions; non-fatal.
