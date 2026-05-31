"""Tests for the C++ concrete grammar — qualified_identifier extract_name quirk."""
from __future__ import annotations

from pathlib import Path

from slop.tree.parse import parse_file
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


def _first_function(tree):
    """Return the first ``function_definition`` node in a parsed tree."""
    stack = [tree.root_node]
    while stack:
        n = stack.pop()
        if n.type == "function_definition":
            return n
        stack.extend(n.children)
    raise AssertionError("function_definition not found")


def _parse_fn(tmp_path: Path, src: str):
    """Parse one C++ snippet, returning (first_function_node, content)."""
    p = tmp_path / "x.cpp"
    p.write_text(src)
    parsed = parse_file(p, "cpp")
    assert parsed is not None
    tree, content = parsed
    return _first_function(tree), content


class TestCppExtractNameShapes:
    """Characterization of extract_name's declarator-inner branches.

    Locks current behavior — including the out-of-line destructor
    returning ``<anonymous>`` (the qualified_identifier ``S::~S`` holds a
    destructor_name, not a plain identifier) — before the helper split.
    """

    def test_operator_overload(self, tmp_path: Path):
        fn, content = _parse_fn(tmp_path, "struct S{}; S operator+(const S& a, const S& b){ return a; }\n")
        assert Cpp.extract_name(fn, content) == "+"

    def test_pointer_return_type(self, tmp_path: Path):
        fn, content = _parse_fn(tmp_path, "int* get(int* p){ return p; }\n")
        assert Cpp.extract_name(fn, content) == "get"

    def test_out_of_line_destructor_is_anonymous(self, tmp_path: Path):
        fn, content = _parse_fn(tmp_path, "struct S{ ~S(); }; S::~S(){ }\n")
        assert Cpp.extract_name(fn, content) == "<anonymous>"


class TestCppHiddenMutators:
    """Characterization of the non-const pointer/reference mutation finder.

    Locks current behavior before the navigation-helper extraction:
    declarator unwrapping (pointer/reference return types), pointer
    mutation shapes (deref / field / subscript), reference mutation
    shapes (assign / field-assign), and const-skipping.
    """

    def test_pointer_deref_assign(self, tmp_path: Path):
        fn, content = _parse_fn(tmp_path, "void f(int* p) { *p = 5; }\n")
        assert Cpp.hidden_mutators(fn, content) == [("p", "deref-assign", 1)]

    def test_pointer_field_assign(self, tmp_path: Path):
        fn, content = _parse_fn(tmp_path, "struct S{int x;}; void f(S* p) { p->x = 5; }\n")
        assert Cpp.hidden_mutators(fn, content) == [("p", "field-assign", 1)]

    def test_pointer_subscript_assign(self, tmp_path: Path):
        fn, content = _parse_fn(tmp_path, "void f(int* p) { p[0] = 5; }\n")
        assert Cpp.hidden_mutators(fn, content) == [("p", "subscript-assign", 1)]

    def test_const_pointer_skipped(self, tmp_path: Path):
        fn, content = _parse_fn(tmp_path, "void f(const int* p) { int y = *p; }\n")
        assert Cpp.hidden_mutators(fn, content) == []

    def test_reference_assign(self, tmp_path: Path):
        fn, content = _parse_fn(tmp_path, "void f(int& r) { r = 5; }\n")
        assert Cpp.hidden_mutators(fn, content) == [("r", "ref-assign", 1)]

    def test_reference_field_assign(self, tmp_path: Path):
        fn, content = _parse_fn(tmp_path, "struct S{int x;}; void f(S& r) { r.x = 5; }\n")
        assert Cpp.hidden_mutators(fn, content) == [("r", "ref-field-assign", 1)]

    def test_pointer_return_type_unwrapped(self, tmp_path: Path):
        # ``int* g(...)`` wraps the function_declarator in a pointer_declarator.
        fn, content = _parse_fn(tmp_path, "int* g(int* p) { *p = 1; return p; }\n")
        assert Cpp.hidden_mutators(fn, content) == [("p", "deref-assign", 1)]

    def test_no_params(self, tmp_path: Path):
        fn, content = _parse_fn(tmp_path, "void f() { int x = 1; }\n")
        assert Cpp.hidden_mutators(fn, content) == []

    def test_pointer_and_reference_together(self, tmp_path: Path):
        fn, content = _parse_fn(tmp_path, "void f(int* p, int& r) { *p = 1; r = 2; }\n")
        out = Cpp.hidden_mutators(fn, content)
        assert ("p", "deref-assign", 1) in out
        assert ("r", "ref-assign", 1) in out
        assert len(out) == 2


class TestCppStringlyTypedParams:
    """Characterization of the string-typed parameter finder.

    Locks: char*, std::string (qualified_identifier), string_view
    (type_identifier), qualified string_view, const char*, and the
    non-string skip path. Every hit returns ``(name, True)``.
    """

    def test_char_pointer(self, tmp_path: Path):
        fn, content = _parse_fn(tmp_path, "void f(char* s) { }\n")
        assert Cpp.stringly_typed_params(fn, content) == [("s", True)]

    def test_std_string_qualified(self, tmp_path: Path):
        fn, content = _parse_fn(tmp_path, "void f(std::string s) { }\n")
        assert Cpp.stringly_typed_params(fn, content) == [("s", True)]

    def test_string_view_type_identifier(self, tmp_path: Path):
        fn, content = _parse_fn(tmp_path, "using namespace std; void f(string_view s) { }\n")
        assert Cpp.stringly_typed_params(fn, content) == [("s", True)]

    def test_qualified_string_view(self, tmp_path: Path):
        fn, content = _parse_fn(tmp_path, "void f(std::string_view s) { }\n")
        assert Cpp.stringly_typed_params(fn, content) == [("s", True)]

    def test_const_char_pointer_still_string(self, tmp_path: Path):
        # stringly does not const-skip (unlike hidden_mutators).
        fn, content = _parse_fn(tmp_path, "void f(const char* s) { }\n")
        assert Cpp.stringly_typed_params(fn, content) == [("s", True)]

    def test_non_string_skipped(self, tmp_path: Path):
        fn, content = _parse_fn(tmp_path, "void f(int n) { }\n")
        assert Cpp.stringly_typed_params(fn, content) == []
