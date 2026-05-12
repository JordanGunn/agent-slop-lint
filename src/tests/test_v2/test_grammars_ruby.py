"""Tests for the Ruby concrete grammar — positional def extract_name quirk."""
from __future__ import annotations

from pathlib import Path

from slop._ast.treesitter import parse_file
from slop.language.grammars import Ruby


class TestRubyExtraction:
    def test_id_is_ruby(self):
        assert Ruby.id == "ruby"

    def test_extract_name_for_regular_method(self, tmp_path: Path):
        src = tmp_path / "x.rb"
        src.write_text("def foo\n  1\nend\n")
        parsed = parse_file(src, "ruby")
        assert parsed is not None
        tree, content = parsed
        for child in tree.root_node.children:
            if child.type == "method":
                assert Ruby.extract_name(child, content) == "foo"
                return
        raise AssertionError("method not found")

    def test_extract_name_for_singleton_method(self, tmp_path: Path):
        src = tmp_path / "x.rb"
        src.write_text("def self.bar\n  1\nend\n")
        parsed = parse_file(src, "ruby")
        assert parsed is not None
        tree, content = parsed
        for child in tree.root_node.children:
            if child.type == "singleton_method":
                assert Ruby.extract_name(child, content) == "bar"
                return
        raise AssertionError("singleton_method not found")
