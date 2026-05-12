"""Smoke tests for the remaining 7 grammars.

Each grammar parses a 2-callable fixture and produces 2 callables of
the right kind. Goes shallow — quirk overrides have their own files.
"""
from __future__ import annotations

from pathlib import Path

from slop.tree.tree import Tree
from slop.language.grammars import (
    CSharp,
    Go,
    Java,
    JavaScript,
    Julia,
    Rust,
    TypeScript,
)


def _scan(path: Path):
    cb = Tree(path)
    cb.scan()
    return cb


def test_javascript_parses_two_callables(tmp_path: Path):
    (tmp_path / "x.js").write_text("function a() { return 1; }\nfunction b() { return 2; }\n")
    cb = _scan(tmp_path)
    assert "javascript" in cb.languages_detected
    assert sum(1 for _ in cb.structure.callables()) >= 2


def test_typescript_parses_two_callables(tmp_path: Path):
    (tmp_path / "x.ts").write_text(
        "function a(): number { return 1; }\nfunction b(): number { return 2; }\n"
    )
    cb = _scan(tmp_path)
    assert "typescript" in cb.languages_detected
    assert sum(1 for _ in cb.structure.callables()) >= 2


def test_go_parses_two_callables(tmp_path: Path):
    (tmp_path / "x.go").write_text(
        "package p\nfunc a() int { return 1 }\nfunc b() int { return 2 }\n"
    )
    cb = _scan(tmp_path)
    assert "go" in cb.languages_detected
    assert sum(1 for _ in cb.structure.callables()) >= 2


def test_rust_parses_two_callables(tmp_path: Path):
    (tmp_path / "x.rs").write_text("fn a() -> i32 { 1 }\nfn b() -> i32 { 2 }\n")
    cb = _scan(tmp_path)
    assert "rust" in cb.languages_detected
    assert sum(1 for _ in cb.structure.callables()) >= 2


def test_julia_parses_two_callables(tmp_path: Path):
    (tmp_path / "x.jl").write_text("function a() 1 end\nfunction b() 2 end\n")
    cb = _scan(tmp_path)
    assert "julia" in cb.languages_detected
    assert sum(1 for _ in cb.structure.callables()) >= 2


def test_java_parses_class_with_two_methods(tmp_path: Path):
    (tmp_path / "X.java").write_text(
        "public class X {\n    int a() { return 1; }\n    int b() { return 2; }\n}\n"
    )
    cb = _scan(tmp_path)
    assert "java" in cb.languages_detected
    assert sum(1 for _ in cb.structure.callables()) >= 2


def test_csharp_parses_class_with_two_methods(tmp_path: Path):
    (tmp_path / "X.cs").write_text(
        "class X { int a() { return 1; } int b() { return 2; } }\n"
    )
    cb = _scan(tmp_path)
    assert "c_sharp" in cb.languages_detected
    assert sum(1 for _ in cb.structure.callables()) >= 2
