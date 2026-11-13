"""Complexity family — cyclomatic / cognitive / combinatorial / halstead."""
from __future__ import annotations

from pathlib import Path

from slop.metrics.structural import halstead
from slop.metrics.structural.view import Structure
from slop.scope import scan_corpus

SRC = '''\
def h(x, y):
    if x:
        if y and x > 0:
            return 1
    for i in range(x):
        while i:
            pass
    return 0

def branchy(a):
    if a > 0:
        return 1
    elif a < 0:
        return 2
    else:
        return 3
'''


def _callables(tmp_path: Path) -> dict:
    (tmp_path / "m.py").write_text(SRC)
    corpus = scan_corpus(tmp_path, config=None)
    return {c.qualname: c for c in corpus._iter_callables()}


def test_cyclomatic(tmp_path: Path):
    cs = _callables(tmp_path)
    assert Structure.over(cs["m.h"]).cyclomatic() == 6
    assert Structure.over(cs["m.branchy"]).cyclomatic() == 3


def test_cognitive(tmp_path: Path):
    cs = _callables(tmp_path)
    assert Structure.over(cs["m.h"]).cognitive() == 7
    assert Structure.over(cs["m.branchy"]).cognitive() == 2


def test_combinatorial_npath(tmp_path: Path):
    cs = _callables(tmp_path)
    assert Structure.over(cs["m.h"]).combinatorial() == 9
    assert Structure.over(cs["m.branchy"]).combinatorial() == 3


def test_halstead(tmp_path: Path):
    cs = _callables(tmp_path)
    assert round(Structure.over(cs["m.h"]).volume(), 2) == 76.15


def test_a_string_literal_is_one_operand_not_zero(tmp_path: Path):
    # A Python string is a node with string_start / string_content children, not a leaf.
    (tmp_path / "s.py").write_text('def s():\n    return "a b"\n\ndef t():\n    return "a b" + "a b" + "c"\n')
    cs = {c.qualname: c for c in scan_corpus(tmp_path, config=None)._iter_callables()}
    one, many = _counts(cs["s.s"]), _counts(cs["s.t"])
    assert (one[1], one[3]) == (1, 1)              # distinct and total operands
    assert (many[1], many[3]) == (2, 3)


def test_aggregation_sums_volume(tmp_path: Path):
    (tmp_path / "m.py").write_text(SRC)
    corpus = scan_corpus(tmp_path, config=None)
    mod = corpus.realms()[0].packages()[0].modules()[0]
    total = sum(Structure.over(c).volume() for c in corpus._iter_callables())
    assert round(Structure.over(mod).volume(), 4) == round(total, 4)


def test_halstead_does_not_count_a_nested_callable_in_its_parent(tmp_path: Path):
    (tmp_path / "n.py").write_text("def outer(x):\n    def inner(y):\n        return y * 99 + y * 98\n    return x\n")
    cs = {c.qualname: c for c in scan_corpus(tmp_path, config=None)._iter_callables()}
    assert _counts(cs["n.outer"]) == (1, 1, 1, 1)       # `return x` only


def test_julia_infix_operators_are_counted(tmp_path: Path):
    # Julia types every infix operator token `operator` and puts the symbol in the text.
    (tmp_path / "j.jl").write_text("function f(x)\n    x * 9.81 + x\nend\n")
    [c] = scan_corpus(tmp_path, config=None)._iter_callables()
    n1, _n2, N1, _N2 = _counts(c)
    assert n1 >= 2 and N1 >= 2          # `*` and `+`


def test_cpp_counts_a_plain_body_like_c(tmp_path: Path):
    # `operator` is in the C++ operator set (the keyword in `operator+`); it must not
    # change the count of a body that has none.
    (tmp_path / "a.c").write_text("double f(double x) { return x * 9.81 + x; }\n")
    (tmp_path / "b.cpp").write_text("double g(double x) { return x * 9.81 + x; }\n")
    counted = {c.qualname: _counts(c) for c in scan_corpus(tmp_path, config=None)._iter_callables()}
    assert counted["a.f"] == counted["b.g"]


def _counts(callable_):
    """(η1, η2, N1, N2) of one callable: distinct and total operators and operands."""
    return halstead.counts(callable_._ast_node(), callable_._grammar)
