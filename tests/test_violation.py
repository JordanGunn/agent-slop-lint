"""Violation: located at the definition of a scope (1-based line and column), at a package's
directory for a package, and carrying nothing but rule, place, message and the numbers."""
from __future__ import annotations

from pathlib import Path

from slop.scope import scan_corpus
from slop.scope.identity import ScopeKind
from slop.violation import Violation

SRC = (
    "import os\n"                 # 1
    "\n"                          # 2
    "class Outer:\n"              # 3
    "    def method(self):\n"     # 4
    "        return 1\n"          # 5
    "\n"                          # 6
    "def top():\n"                # 7
    "    return 2\n"              # 8
)


def _scopes(tmp_path: Path) -> dict[str, object]:
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("")
    (tmp_path / "pkg" / "m.py").write_text(SRC)
    corpus = scan_corpus(tmp_path, config=None)
    out: dict[str, object] = {}
    stack = [corpus]
    while stack:
        s = stack.pop()
        if s.id.kind in (ScopeKind.CALLABLE, ScopeKind.CLASS) or \
                (s.id.kind is ScopeKind.MODULE and s.qualname.endswith("m")) or \
                (s.id.kind is ScopeKind.PACKAGE):
            out[f"{s.id.kind.value}:{s.qualname}"] = s
        stack.extend(s.children())
    return out


def test_a_callable_is_located_at_its_definition(tmp_path: Path):
    scopes = _scopes(tmp_path)
    method = next(s for k, s in scopes.items() if k.startswith("callable:") and k.endswith("method"))
    v = Violation.at(method, "r.x", "msg", value=3, threshold=2)
    assert (v.line, v.column) == (4, 5)                # 1-based, indented under the class
    assert v.path == str(tmp_path / "pkg" / "m.py")
    assert (v.rule, v.message, v.value, v.threshold) == ("r.x", "msg", 3, 2)


def test_a_top_level_callable_starts_at_column_one(tmp_path: Path):
    scopes = _scopes(tmp_path)
    top = next(s for k, s in scopes.items() if k.startswith("callable:") and k.endswith("top"))
    v = Violation.at(top, "r.x", "msg")
    assert (v.line, v.column) == (7, 1)
    assert v.value is None and v.threshold is None


def test_a_class_is_located_at_its_definition(tmp_path: Path):
    scopes = _scopes(tmp_path)
    cls = next(s for k, s in scopes.items() if k.startswith("class:"))
    assert (Violation.at(cls, "r.x", "m").line, Violation.at(cls, "r.x", "m").column) == (3, 1)


def test_a_module_is_located_at_line_one_column_one(tmp_path: Path):
    scopes = _scopes(tmp_path)
    module = next(s for k, s in scopes.items() if k.startswith("module:"))
    v = Violation.at(module, "r.x", "m")
    assert (v.line, v.column) == (1, 1)
    assert v.path == str(tmp_path / "pkg" / "m.py")


def test_a_package_is_located_at_its_directory(tmp_path: Path):
    scopes = _scopes(tmp_path)
    package = next(s for k, s in scopes.items() if k.startswith("package:") and "pkg" in k)
    v = Violation.at(package, "r.x", "m")
    assert v.path == str(tmp_path / "pkg")
    assert (v.line, v.column) == (1, 1)


def test_as_dict_has_exactly_the_reported_fields():
    v = Violation("r.x", "a/b.py", 2, 3, "msg", value=5, threshold=4, subject="b.f")
    assert v.as_dict() == {"rule": "r.x", "path": "a/b.py", "line": 2, "column": 3,
                           "message": "msg", "value": 5, "threshold": 4, "subject": "b.f"}
    assert not {"severity", "action", "prescription", "confidence", "evidence"} & set(v.as_dict())


def test_a_violation_is_immutable():
    import dataclasses

    import pytest
    v = Violation("r.x", None, 1, 1, "m")
    with pytest.raises(dataclasses.FrozenInstanceError):
        v.line = 2  # type: ignore[misc]
