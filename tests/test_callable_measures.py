"""magic_literals: numeric literals that are operands of an operator."""
from __future__ import annotations

from pathlib import Path

import pytest

from slop.metrics.structural.view import Structure
from slop.scope import scan_corpus


def _magic(tmp_path: Path, filename: str, source: str) -> dict[str, list[str]]:
    (tmp_path / filename).write_text(source)
    corpus = scan_corpus(tmp_path, config=None)
    return {c.qualname.split(".", 1)[1]: [m.value for m in Structure.over(c).magic_literals()]
            for c in corpus._iter_callables()}


def test_operands_of_comparisons_and_arithmetic_are_magic(tmp_path: Path):
    found = _magic(tmp_path, "m.py", "def f(x):\n    if x > 15:\n        return x * 86400 + -9\n    return x\n")
    assert found["f"] == ["15", "86400", "9"]


def test_named_or_positional_numbers_are_not_magic(tmp_path: Path):
    found = _magic(tmp_path, "m.py", (
        "def f(a, x=10):\n"
        "    timeout = 30\n"          # named by assignment
        "    k = a[3]\n"              # index
        "    s = a[1:4]\n"            # slice
        "    g(timeout=5)\n"          # keyword argument
        "    return a\n"))
    assert found["f"] == []


def test_a_literal_beside_a_keyword_is_not_an_operand(tmp_path: Path):
    # `return` and `if` are in the grammar's operator set; `return 3` is not an operation.
    found = _magic(tmp_path, "m.py", "def f(x):\n    if x:\n        return 3\n    return 4\n")
    assert found["f"] == []


def test_ordinary_values_and_repeats_are_not_reported(tmp_path: Path):
    found = _magic(tmp_path, "m.py", "def f(x):\n    return x * 2 + x * 7 + x * 7 + x - 1 + x * 0\n")
    assert found["f"] == ["7"]


def test_a_nested_callable_is_not_charged_to_its_parent(tmp_path: Path):
    found = _magic(tmp_path, "m.py", "def outer(x):\n    def inner(y):\n        return y * 99\n    return x\n")
    assert found["outer"] == [] and found["outer.inner"] == ["99"]


@pytest.mark.parametrize("filename, source", [
    ("m.ts", "function f(x: number) { return x > 15; }\n"),
    ("m.go", "package p\nfunc f(x int) bool {\n\treturn x > 15\n}\n"),
    ("m.js", "function f(x) { return x > 15; }\n"),
    ("m.rs", "fn f(x: i32) -> bool { x > 15 }\n"),
])
def test_other_grammars_read_the_same_context(tmp_path: Path, filename: str, source: str):
    assert list(_magic(tmp_path, filename, source).values()) == [["15"]]


def test_a_type_keyword_named_like_a_literal_is_not_a_number(tmp_path: Path):
    # TypeScript's `predefined_type` child has the node type `number`, which is also the
    # numeric-literal type. Its text is the word "number".
    found = _magic(tmp_path, "m.ts", "function f(x: number, y: number) { return x + y; }\n")
    assert found["f"] == []


def test_a_repeated_literal_is_reported_once_at_its_first_line(tmp_path: Path):
    (tmp_path / "m.py").write_text("def f(x):\n    a = x * 7\n    b = x * 7\n    return a + b\n")
    [c] = scan_corpus(tmp_path, config=None)._iter_callables()
    [m] = Structure.over(c).magic_literals()
    assert (m.value, m.line) == ("7", 2)
