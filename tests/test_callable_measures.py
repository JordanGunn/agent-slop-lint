"""Callable non-aggregatable measures: magic literals, mutators, sentinels."""
from __future__ import annotations

from pathlib import Path

from slop.metrics.structural.view import Structure
from slop.scope import scan_corpus

SRC = '''\
def cfg(timeout, mode: str, count):
    x = 3600
    y = 42
    z = 1
    return timeout * x

def mutate(items: list):
    items.append(1)
    return items
'''


def _cs(tmp_path: Path) -> dict:
    (tmp_path / "x.py").write_text(SRC)
    return {c.qualname: c for c in scan_corpus(tmp_path, config=None)._iter_callables()}


def test_magic_literals_excludes_trivials(tmp_path: Path):
    cfg = _cs(tmp_path)["x.cfg"]
    assert sorted(m.value for m in Structure.over(cfg).magic_literals()) == ["3600", "42"]  # 1 is trivial


def test_sentinel_parameters(tmp_path: Path):
    cfg = _cs(tmp_path)["x.cfg"]
    assert [s.name for s in Structure.over(cfg).sentinel_parameters()] == ["mode"]


def test_mutated_parameters(tmp_path: Path):
    mut = _cs(tmp_path)["x.mutate"]
    assert [(p.parameter, p.kind) for p in Structure.over(mut).mutated_parameters()] == [("items", "append")]
