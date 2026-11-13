"""A callable's kind: function, method, lambda, constructor or accessor."""
from __future__ import annotations

from pathlib import Path

import pytest

from slop.identity import CallableKind
from slop.scope import scan_corpus
from slop.scope.find import walk
from slop.scope.identity import ScopeKind


def _kinds(tmp_path: Path, name: str, source: str) -> dict[str, CallableKind]:
    (tmp_path / name).write_text(source, encoding="utf-8")
    corpus = scan_corpus(tmp_path, config=None)
    return {s.name: s.kind for s in walk(corpus) if s.id.kind is ScopeKind.CALLABLE}


@pytest.mark.parametrize("name, source, expected", [
    ("m.py", "class A:\n    def __init__(self):\n        self.a = 1\n    def a_value(self):\n        return self.a\n"
             "    def run(self):\n        return self.a * 2\n\ndef free():\n    return 1\n",
     {"__init__": CallableKind.CONSTRUCTOR, "a_value": CallableKind.ACCESSOR, "run": CallableKind.METHOD,
      "free": CallableKind.FUNCTION}),
    ("A.java", "class A { int x; A() { x = 0; } int run() { return x * 2; } }",
     {"A": CallableKind.CONSTRUCTOR, "run": CallableKind.METHOD}),
    ("m.ts", "class A {\n  constructor() { this.a = 1 }\n  run() { return this.a * 2 }\n}\n",
     {"constructor": CallableKind.CONSTRUCTOR, "run": CallableKind.METHOD}),
])
def test_constructors_are_their_own_kind_and_never_accessors(tmp_path: Path, name: str, source: str, expected):
    assert {n: k for n, k in _kinds(tmp_path, name, source).items() if n in expected} == expected
