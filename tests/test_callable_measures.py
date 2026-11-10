"""Callable non-aggregatable measure: magic literals."""
from __future__ import annotations

from pathlib import Path

from slop.metrics.structural.view import Structure
from slop.scope import scan_corpus

SRC = '''\
def cfg(timeout, count):
    x = 3600
    y = 42
    z = 1
    return timeout * x
'''


def _cs(tmp_path: Path) -> dict:
    (tmp_path / "x.py").write_text(SRC)
    return {c.qualname: c for c in scan_corpus(tmp_path, config=None)._iter_callables()}


def test_magic_literals_excludes_trivials(tmp_path: Path):
    cfg = _cs(tmp_path)["x.cfg"]
    assert sorted(m.value for m in Structure.over(cfg).magic_literals()) == ["3600", "42"]  # 1 is trivial
