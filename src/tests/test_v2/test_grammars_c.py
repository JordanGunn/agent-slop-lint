"""Tests for the C concrete grammar — declarator-chain extract_name quirk."""
from __future__ import annotations

from pathlib import Path

from slop.tree.parse import parse_file
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


def _first_function(tree):
    stack = [tree.root_node]
    while stack:
        n = stack.pop()
        if n.type == "function_definition":
            return n
        stack.extend(n.children)
    raise AssertionError("function_definition not found")


def _parse_fn(tmp_path: Path, src: str):
    p = tmp_path / "x.c"
    p.write_text(src)
    parsed = parse_file(p, "c")
    assert parsed is not None
    tree, content = parsed
    return _first_function(tree), content


class TestCHiddenMutators:
    """Characterization of pointer-parameter mutation detection.

    Locks the three LHS shapes (deref ``*p =``, field ``p->x =``, subscript
    ``p[i] =``), const-skipping, and the no-param path before the
    navigation-helper extraction.
    """

    def test_deref_assign(self, tmp_path: Path):
        fn, content = _parse_fn(tmp_path, "void f(int* p){ *p=5; }\n")
        assert C.hidden_mutators(fn, content) == [("p", "deref-assign", 1)]

    def test_field_arrow_assign(self, tmp_path: Path):
        fn, content = _parse_fn(tmp_path, "struct S{int x;}; void f(struct S* p){ p->x=5; }\n")
        assert C.hidden_mutators(fn, content) == [("p", "field-assign", 1)]

    def test_subscript_assign(self, tmp_path: Path):
        fn, content = _parse_fn(tmp_path, "void f(int* p){ p[0]=5; }\n")
        assert C.hidden_mutators(fn, content) == [("p", "subscript-assign", 1)]

    def test_const_pointer_skipped(self, tmp_path: Path):
        fn, content = _parse_fn(tmp_path, "void f(const int* p){ int y=*p; }\n")
        assert C.hidden_mutators(fn, content) == []

    def test_no_params(self, tmp_path: Path):
        fn, content = _parse_fn(tmp_path, "void f(){ int x=1; }\n")
        assert C.hidden_mutators(fn, content) == []

    def test_two_pointers(self, tmp_path: Path):
        fn, content = _parse_fn(tmp_path, "void f(int* a, int* b){ *a=1; b[2]=3; }\n")
        out = C.hidden_mutators(fn, content)
        assert ("a", "deref-assign", 1) in out
        assert ("b", "subscript-assign", 1) in out
        assert len(out) == 2


class TestCStringlyTypedParams:
    """Characterization: only ``char*`` (pointer) params count; bare ``char`` does not."""

    def test_char_pointer(self, tmp_path: Path):
        fn, content = _parse_fn(tmp_path, "void f(char* s){}\n")
        assert C.stringly_typed_params(fn, content) == [("s", True)]

    def test_const_char_pointer_still_string(self, tmp_path: Path):
        fn, content = _parse_fn(tmp_path, "void f(const char* s){}\n")
        assert C.stringly_typed_params(fn, content) == [("s", True)]

    def test_non_char_skipped(self, tmp_path: Path):
        fn, content = _parse_fn(tmp_path, "void f(int n){}\n")
        assert C.stringly_typed_params(fn, content) == []

    def test_bare_char_without_pointer_skipped(self, tmp_path: Path):
        fn, content = _parse_fn(tmp_path, "void f(char c){}\n")
        assert C.stringly_typed_params(fn, content) == []
