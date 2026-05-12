"""Shared fixtures for v2 substrate tests.

Each fixture builds a tiny in-memory corpus via ``tmp_path``. Fixtures
are designed for the smallest possible source that exercises the
intended substrate surface.
"""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def tiny_corpus(tmp_path: Path) -> Path:
    """Two Python files, ~5 callables each. Drives Tree.scan smoke."""
    (tmp_path / "a.py").write_text(
        "def alpha(x):\n    return x\n\n"
        "def beta(y):\n    if y:\n        return y\n    return None\n\n"
        "class Cls:\n"
        "    def method_a(self): return 1\n"
        "    def method_b(self, y): return y\n"
    )
    (tmp_path / "b.py").write_text(
        "def gamma(z):\n    for i in range(z):\n        print(i)\n\n"
        "def delta(a, b):\n    return a + b\n"
    )
    return tmp_path


@pytest.fixture
def polyglot_corpus(tmp_path: Path) -> Path:
    """One trivial file per language; drives languages_detected."""
    (tmp_path / "a.py").write_text("def foo(): return 1\n")
    (tmp_path / "a.js").write_text("function foo() { return 1; }\n")
    (tmp_path / "a.ts").write_text("function foo(): number { return 1; }\n")
    (tmp_path / "a.go").write_text("package p\nfunc foo() int { return 1 }\n")
    (tmp_path / "a.rs").write_text("fn foo() -> i32 { 1 }\n")
    (tmp_path / "a.rb").write_text("def foo; 1; end\n")
    (tmp_path / "a.c").write_text("int foo(void) { return 1; }\n")
    return tmp_path


@pytest.fixture
def cluster_corpus(tmp_path: Path) -> Path:
    """Four functions sharing first parameter `node` — drives imposters' first_param_clusters."""
    (tmp_path / "walker.py").write_text(
        "def walk_assign(node):\n    return node.left\n\n"
        "def walk_call(node):\n    return node.func\n\n"
        "def walk_attr(node):\n    return node.attr\n\n"
        "def walk_const(node):\n    return node.value\n"
    )
    return tmp_path


@pytest.fixture
def class_corpus(tmp_path: Path) -> Path:
    """Module with 2 classes (3 methods each) + 1 free function. Drives in_class flipping."""
    (tmp_path / "m.py").write_text(
        "class A:\n"
        "    def a1(self): return 1\n"
        "    def a2(self): return 2\n"
        "    def a3(self): return 3\n\n"
        "class B:\n"
        "    def b1(self): return 1\n"
        "    def b2(self): return 2\n"
        "    def b3(self): return 3\n\n"
        "def free_fn(x):\n    return x\n"
    )
    return tmp_path


@pytest.fixture
def complexity_corpus(tmp_path: Path) -> Path:
    """Canonical complexity cases: linear, single-if, if-else-in-loop, nested."""
    (tmp_path / "c.py").write_text(
        # CCX 1: linear straight-through
        "def linear():\n    x = 1\n    y = 2\n    return x + y\n\n"
        # CCX 2: one if
        "def single_if(x):\n    if x:\n        return 1\n    return 0\n\n"
        # CCX 3: if-else inside loop (loop=+1, if=+1, base=+1)
        "def if_in_loop(items):\n"
        "    for i in items:\n"
        "        if i:\n"
        "            print(i)\n"
        "    return None\n\n"
        # CCX 5: 4 nested decisions
        "def nested(a, b, c, d):\n"
        "    if a:\n"
        "        if b:\n"
        "            if c:\n"
        "                if d:\n"
        "                    return 1\n"
        "    return 0\n"
    )
    return tmp_path
