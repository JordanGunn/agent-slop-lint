"""Tests for the Tree walk — scope/callable/occurrence emission, in_class flipping."""
from __future__ import annotations

from pathlib import Path

from slop.tree.tree import Tree
from slop.tree.records import CallableKind, ScopeKind


def _scan(path: Path) -> Tree:
    cb = Tree(path)
    cb.scan()
    return cb


class TestWalkEmission:
    def test_emits_file_scope_per_file(self, tiny_corpus: Path):
        cb = _scan(tiny_corpus)
        file_scopes = [s for s in cb.structure.scopes() if s.kind == ScopeKind.FILE]
        assert len(file_scopes) == 2  # a.py + b.py

    def test_class_corpus_emits_one_class_per_class_definition(self, class_corpus: Path):
        cb = _scan(class_corpus)
        class_scopes = [s for s in cb.structure.scopes() if s.kind == ScopeKind.CLASS]
        assert len(class_scopes) == 2  # A + B


class TestInClassFlipping:
    def test_methods_inside_class_tagged_method_not_function(self, class_corpus: Path):
        cb = _scan(class_corpus)
        methods = [c for c in cb.structure.callables() if c.kind == CallableKind.METHOD]
        # 3 methods × 2 classes = 6 methods
        assert len(methods) == 6

    def test_free_function_tagged_function_not_method(self, class_corpus: Path):
        cb = _scan(class_corpus)
        funcs = [c for c in cb.structure.callables() if c.kind == CallableKind.FUNCTION]
        # The corpus has exactly one free function: free_fn
        assert any(c.qualname.endswith("free_fn") for c in funcs)


class TestParentTracking:
    def test_method_parent_is_class_qualname(self, class_corpus: Path):
        cb = _scan(class_corpus)
        for c in cb.structure.callables():
            if c.qualname.endswith("a1"):
                assert c.parent is not None
                assert c.parent.endswith("A")
                return
        raise AssertionError("a1 method not found")
