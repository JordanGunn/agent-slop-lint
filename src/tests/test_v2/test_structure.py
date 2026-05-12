"""Tests for ``slop.structure.view.Structure``."""
from __future__ import annotations

from pathlib import Path

from slop.tree.tree import Tree
from slop.tree.records import CallableKind, ScopeKind


def _structure(path: Path):
    cb = Tree(path)
    cb.scan()
    return cb.structure


class TestIterationAndLookup:
    def test_callables_yields_all(self, tiny_corpus: Path):
        s = _structure(tiny_corpus)
        names = {c.qualname.split(".")[-1] for c in s.callables()}
        # tiny_corpus has alpha, beta, gamma, delta + Cls.method_a + Cls.method_b
        assert {"alpha", "beta", "gamma", "delta", "method_a", "method_b"} <= names

    def test_scope_lookup_by_qualname(self, class_corpus: Path):
        s = _structure(class_corpus)
        # Find any class scope and confirm lookup roundtrips.
        for sc in s.scopes():
            if sc.kind == ScopeKind.CLASS:
                found = s.scope(sc.qualname)
                assert found is not None
                assert found.qualname == sc.qualname
                return
        raise AssertionError("no class scope found")

    def test_children_returns_methods_of_class(self, class_corpus: Path):
        s = _structure(class_corpus)
        for sc in s.scopes():
            if sc.kind == ScopeKind.CLASS and sc.qualname.endswith("A"):
                kids = list(s.children(sc.qualname))
                # Class A has 3 methods (a1, a2, a3)
                assert len(kids) == 3
                return
        raise AssertionError("class A not found")


class TestSlicing:
    def test_where_kind_returns_new_structure(self, class_corpus: Path):
        s = _structure(class_corpus)
        narrowed = s.where(kind=CallableKind.METHOD)
        assert narrowed is not s
        # Parent unaffected: all kinds still present.
        all_kinds = {c.kind for c in s.callables()}
        assert all_kinds >= {CallableKind.METHOD, CallableKind.FUNCTION}

    def test_under_path_filters_by_prefix(self, tiny_corpus: Path):
        s = _structure(tiny_corpus)
        narrowed = s.under(path=str(tiny_corpus / "a.py"))
        narrowed_callables = list(narrowed.callables())
        # Only callables from a.py
        for c in narrowed_callables:
            assert "a.py" in str(c.path)


class TestCyclomatic:
    def test_linear_is_one(self, complexity_corpus: Path):
        s = _structure(complexity_corpus)
        for c in s.callables():
            if c.qualname.endswith("linear"):
                assert s.cyclomatic(c) == 1
                return
        raise AssertionError("linear not found")

    def test_single_if_is_two(self, complexity_corpus: Path):
        s = _structure(complexity_corpus)
        for c in s.callables():
            if c.qualname.endswith("single_if"):
                assert s.cyclomatic(c) == 2
                return
        raise AssertionError("single_if not found")

    def test_if_in_loop_is_three(self, complexity_corpus: Path):
        s = _structure(complexity_corpus)
        for c in s.callables():
            if c.qualname.endswith("if_in_loop"):
                assert s.cyclomatic(c) == 3
                return
        raise AssertionError("if_in_loop not found")

    def test_nested_four_ifs_is_five(self, complexity_corpus: Path):
        s = _structure(complexity_corpus)
        for c in s.callables():
            if c.qualname.endswith("nested"):
                # 4 decision points + base path = 5
                assert s.cyclomatic(c) == 5
                return
        raise AssertionError("nested not found")
