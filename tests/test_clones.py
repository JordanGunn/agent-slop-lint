"""Type-2 clone clusters over a module's callables."""
from __future__ import annotations

from pathlib import Path

from slop.metrics.structural.view import Structure
from slop.scope import scan_corpus

CLONES = '''\
def dup1(a, b):
    x = a + b
    y = x * 2
    z = y - 1
    return z

def dup2(c, d):
    x = c + d
    y = x * 2
    z = y - 1
    return z
'''


def _module(tmp_path: Path, src: str):
    (tmp_path / "r.py").write_text(src)
    return scan_corpus(tmp_path, config=None).realms()[0].packages()[0].modules()[0]


def test_clone_clusters(tmp_path: Path):
    mod = _module(tmp_path, CLONES)
    clusters = Structure.over(mod).clone_clusters()
    assert len(clusters) == 1
    assert set(clusters[0].members) == {"r.dup1", "r.dup2"}


def test_bodies_that_differ_in_shape_are_not_clones(tmp_path: Path):
    src = CLONES + "\ndef other(a):\n    if a:\n        return a\n    return 0\n"
    mod = _module(tmp_path, src)
    (cluster,) = Structure.over(mod).clone_clusters()
    assert set(cluster.members) == {"r.dup1", "r.dup2"}      # 'other' is not in the family
