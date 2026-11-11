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


def _tables(first: str, second: str) -> str:
    return (f"def a():\n    return frozenset({{{first}}})\n\n"
            f"def b():\n    return frozenset({{{second}}})\n")


def test_constant_tables_with_different_entries_are_not_clones(tmp_path: Path):
    mod = _module(tmp_path, _tables('"alpha", "beta", "gamma", "delta"', '"one", "two", "three", "four"'))
    assert Structure.over(mod).clone_clusters(min_leaf_nodes=5) == []


def test_constant_tables_with_the_same_entries_are_clones(tmp_path: Path):
    entries = '"alpha", "beta", "gamma", "delta"'
    [cluster] = Structure.over(_module(tmp_path, _tables(entries, entries))).clone_clusters(min_leaf_nodes=5)
    assert {m.qualname for m in cluster.members} == {"r.a", "r.b"}


def test_logic_that_differs_only_in_a_literal_is_still_a_clone(tmp_path: Path):
    # Type-2: literal values are discarded. A constant in logic (`* 2` vs `* 3`, a different
    # message) does not make two bodies different.
    src = ("def a(x):\n    y = x * 2\n    z = y + 1\n    if z > 5:\n        raise ValueError('too big')\n    return z\n\n"
           "def b(x):\n    y = x * 3\n    z = y + 9\n    if z > 7:\n        raise ValueError('too large')\n    return z\n")
    [cluster] = Structure.over(_module(tmp_path, src)).clone_clusters(min_leaf_nodes=5)
    assert {m.qualname for m in cluster.members} == {"r.a", "r.b"}


def test_a_table_too_small_to_be_a_clone_is_not_one(tmp_path: Path):
    # Two entries each: `return frozenset({"&&", "||"})` in many grammars is not duplication.
    src = 'def a():\n    return frozenset({"&&", "||"})\n\ndef b():\n    return frozenset({"&&", "||"})\n'
    assert Structure.over(_module(tmp_path, src)).clone_clusters() == []
