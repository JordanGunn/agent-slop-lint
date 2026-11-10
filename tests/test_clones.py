"""Type-2 clone clusters over a module's callables."""
from __future__ import annotations

from pathlib import Path

from slop.identity import relative_path
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
    assert {m.qualname for m in clusters[0].members} == {"r.dup1", "r.dup2"}


def test_bodies_that_differ_in_shape_are_not_clones(tmp_path: Path):
    src = CLONES + "\ndef other(a):\n    if a:\n        return a\n    return 0\n"
    mod = _module(tmp_path, src)
    (cluster,) = Structure.over(mod).clone_clusters()
    assert {m.qualname for m in cluster.members} == {"r.dup1", "r.dup2"}   # 'other' is not in the family


def test_same_named_clones_in_two_packages_are_told_apart(tmp_path: Path):
    # `a/m.py:f` and `b/m.py:f` are both `m.f`; the members must say which file each is in.
    body = "def f(x):\n    y = x + 1\n    if y:\n        return y * 2\n    z = y - 1\n    return z\n"
    for pkg in ("a", "b"):
        (tmp_path / pkg).mkdir()
        (tmp_path / pkg / "__init__.py").write_text("")
        (tmp_path / pkg / "m.py").write_text(body)
    corpus = scan_corpus(tmp_path, config=None)
    (cluster,) = Structure.over(corpus).clone_clusters()
    assert [m.qualname for m in cluster.members] == ["m.f", "m.f"]
    assert [relative_path(m.scope, tmp_path) for m in cluster.members] == ["a/m.py", "b/m.py"]
    assert [m.line for m in cluster.members] == [1, 1]
