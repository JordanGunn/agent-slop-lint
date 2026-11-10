"""magic-float and duplicate-string report objective violations only."""
from __future__ import annotations

from pathlib import Path

import pytest

from slop.config import RuleConfig
from slop.metrics.structural.view import Structure
from slop.rules import RULE_REGISTRY
from slop.rules.duplicate_string import DuplicateStringRule
from slop.rules.magic_float import MagicFloatRule
from slop.scope import scan_corpus
from slop.scope.identity import ScopeKind


def _module(tmp_path: Path, filename: str, source: str):
    (tmp_path / filename).write_text(source)
    corpus = scan_corpus(tmp_path, config=None)
    return next(m for m in _walk(corpus) if m.id.kind is ScopeKind.MODULE)


def _walk(component):
    yield component
    for child in component.children():
        yield from _walk(child)


def _floats(tmp_path: Path, source: str, filename: str = "m.py") -> dict[str, int]:
    return {u.value: u.count for u in Structure.over(_module(tmp_path, filename, source)).magic_floats()}


def _strings(tmp_path: Path, source: str, filename: str = "m.py") -> dict[str, int]:
    return {u.value: u.count for u in Structure.over(_module(tmp_path, filename, source)).repeated_strings()}


def test_defaults_and_registration():
    assert MagicFloatRule.default_config().options == {"limit": 0}
    assert DuplicateStringRule.default_config().options == {"limit": 4, "min_length": 5}
    assert MagicFloatRule.altitudes == DuplicateStringRule.altitudes == frozenset({ScopeKind.MODULE})
    assert {"magic-float", "duplicate-string"} <= {r.name for r in RULE_REGISTRY}


def test_a_float_operand_is_reported(tmp_path: Path):
    assert _floats(tmp_path, "def f(x, r):\n    if r > 0.7:\n        return x * 9.81\n    return x\n") == {
        "0.7": 1, "9.81": 1}


def test_a_float_with_a_name_or_position_is_not_reported(tmp_path: Path):
    assert _floats(tmp_path, (
        "G = 9.81\n"                       # the constant itself
        "def f(a=9.81):\n"                 # default
        "    g(w=9.81)\n"                  # keyword argument
        "    g(9.81)\n"                    # call argument: ambiguous, left to judgement
        "    return a\n")) == {}


def test_integers_and_ordinary_floats_are_never_reported(tmp_path: Path):
    assert _floats(tmp_path, "def f(x):\n    return x * 3 + x * 86400 + x * 0.5 + x * 100.0 + x * 2.0\n") == {}


def test_a_repeated_float_is_one_entry_at_its_first_line(tmp_path: Path):
    module = _module(tmp_path, "m.py", "def f(x):\n    a = x * 9.81\n    b = x * 9.81\n    return a + b * 9.81\n")
    [use] = Structure.over(module).magic_floats()
    assert (use.value, use.line, use.count) == ("9.81", 2, 3)


def test_the_magic_float_limit_is_uses_allowed(tmp_path: Path):
    module = _module(tmp_path, "m.py", "def f(x):\n    return x * 9.81 + x * 9.81\n")
    rule = MagicFloatRule()
    assert len(list(rule.check(module, RuleConfig(name=rule.name, options={"limit": 0})))) == 1
    assert list(rule.check(module, RuleConfig(name=rule.name, options={"limit": 2}))) == []


def test_a_string_used_three_times_is_reported_once_at_its_first_use(tmp_path: Path):
    module = _module(tmp_path, "m.py", 'def f(g):\n    g("hello")\n    g("hello")\n    g("hello")\n')
    rule = DuplicateStringRule()
    [v] = rule.check(module, RuleConfig(name=rule.name, options={"limit": 2, "min_length": 5}))
    assert (v.rule, v.line, v.column, v.value, v.threshold) == ("duplicate-string", 2, 7, 3, 2)
    assert list(rule.check(module, RuleConfig(name=rule.name, options={"limit": 3, "min_length": 5}))) == []


def test_two_uses_short_strings_and_constants_are_not_reported(tmp_path: Path):
    assert _strings(tmp_path, 'def f(g):\n    g("hello")\n    g("hello")\n') == {'"hello"': 2}   # counted, not over the limit
    found = _strings(tmp_path, (
        "def f(g):\n"
        "    g('r'); g('r'); g('r'); g('r')\n"                       # short
        '    g("abcdef")\n'))
    assert found == {'"abcdef"': 1}
    named = _strings(tmp_path, 'NAME = "abcdef"\ndef f(g):\n    g("abcdef")\n    g("abcdef")\n')
    assert named == {'"abcdef"': 2}                                  # the definition is not a use


def test_fstrings_multiline_strings_and_concatenation_fragments_are_not_counted(tmp_path: Path):
    assert _strings(tmp_path, (
        "def f(g, x):\n"
        '    g(f"hello {x}"); g(f"hello {x}")\n'
        '    g("hello" + x); g("hello" + x)\n'
        '    g("""hello\nworld""")\n')) == {}


@pytest.mark.parametrize("filename, source", [
    ("m.py", 'def f(g):\n    g("hello"); g("hello"); g("hello")\n'),
    ("m.js", 'function f(g) { g("hello"); g("hello"); g("hello"); }\n'),
    ("m.ts", 'function f(g: any) { g("hello"); g("hello"); g("hello"); }\n'),
    ("m.go", 'package p\nfunc f() { g("hello"); g("hello"); g("hello") }\n'),
    ("M.java", 'class M { void f() { g("hello"); g("hello"); g("hello"); } }\n'),
    ("m.cs", 'class M { void F() { G("hello"); G("hello"); G("hello"); } }\n'),
    ("m.rs", 'fn f() { g("hello"); g("hello"); g("hello"); }\n'),
    ("m.jl", 'function f()\n    g("hello"); g("hello"); g("hello")\nend\n'),
    ("m.c", 'void f() { g("hello"); g("hello"); g("hello"); }\n'),
    ("m.cpp", 'void f() { g("hello"); g("hello"); g("hello"); }\n'),
    ("m.rb", 'def f\n  g("hello"); g("hello"); g("hello")\nend\n'),
])
def test_repeated_strings_are_found_in_every_grammar(tmp_path: Path, filename: str, source: str):
    assert list(_strings(tmp_path, source, filename).values()) == [3]


@pytest.mark.parametrize("filename, source", [
    ("m.py", "def f(x):\n    return x * 9.81\n"),
    ("m.js", "function f(x) { return x * 9.81; }\n"),
    ("m.ts", "function f(x: number) { return x * 9.81; }\n"),
    ("m.go", "package p\nfunc f(x float64) float64 {\n\treturn x * 9.81\n}\n"),
    ("M.java", "class M { double f(double x) { return x * 9.81; } }\n"),
    ("m.cs", "class M { double F(double x) { return x * 9.81; } }\n"),
    ("m.rs", "fn f(x: f64) -> f64 { x * 9.81 }\n"),
    ("m.jl", "function f(x)\n    x * 9.81\nend\n"),
    ("m.c", "double f(double x) { return x * 9.81; }\n"),
    ("m.cpp", "double f(double x) { return x * 9.81; }\n"),
    ("m.rb", "def f(x)\n  x * 9.81\nend\n"),
])
def test_float_operands_are_found_in_every_grammar(tmp_path: Path, filename: str, source: str):
    assert _floats(tmp_path, source, filename) == {"9.81": 1}
