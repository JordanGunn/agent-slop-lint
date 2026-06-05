"""Complexity family — cyclomatic / cognitive / combinatorial / halstead / sloc.
Values cross-checked against the legacy oracle."""
from __future__ import annotations

from pathlib import Path

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
    assert round(Structure.over(cs["m.h"]).halstead_density(), 2) == 6.67
    prof = Structure.over(cs["m.h"]).halstead()
    assert prof.effort == prof.volume * prof.difficulty


def test_aggregation_sums_volume(tmp_path: Path):
    (tmp_path / "m.py").write_text(SRC)
    corpus = scan_corpus(tmp_path, config=None)
    mod = corpus.realms()[0].packages()[0].modules()[0]
    total = sum(Structure.over(c).volume() for c in corpus._iter_callables())
    assert round(Structure.over(mod).volume(), 4) == round(total, 4)
