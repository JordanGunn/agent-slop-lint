"""Relational Module measures: redundant siblings, call-islands, clone clusters."""
from __future__ import annotations

from pathlib import Path

from slop.model import scan_corpus

REDUNDANT = '''\
def helper_a(): pass
def helper_b(): pass
def helper_c(): pass

def f1():
    helper_a()
    helper_b()
    helper_c()

def f2():
    helper_a()
    helper_b()
    helper_c()

def lonely():
    pass
'''

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


def test_redundant_siblings(tmp_path: Path):
    mod = _module(tmp_path, REDUNDANT)
    pairs = mod.redundant_siblings()
    assert [(p.left, p.right) for p in pairs] == [("f1", "f2")]
    assert pairs[0].shared_callees == ("helper_a", "helper_b", "helper_c")


def test_call_islands(tmp_path: Path):
    mod = _module(tmp_path, REDUNDANT)
    islands = {tuple(i.members) for i in mod.call_islands()}
    assert ("f1", "f2", "helper_a", "helper_b", "helper_c") in islands
    assert ("lonely",) in islands


def test_clone_clusters(tmp_path: Path):
    mod = _module(tmp_path, CLONES)
    clusters = mod.clone_clusters()
    assert len(clusters) == 1
    assert set(clusters[0].members) == {"r.dup1", "r.dup2"}
