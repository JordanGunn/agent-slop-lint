"""Parameterized clone clusters over a module's callables."""
from __future__ import annotations

from pathlib import Path

import pytest


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
    # Literal values are discarded. A constant in logic (`* 2` vs `* 3`, a different
    # message) does not make two bodies different.
    src = ("def a(x):\n    y = x * 2\n    z = y + 1\n    if z > 5:\n        raise ValueError('too big')\n    return z\n\n"
           "def b(x):\n    y = x * 3\n    z = y + 9\n    if z > 7:\n        raise ValueError('too large')\n    return z\n")
    [cluster] = Structure.over(_module(tmp_path, src)).clone_clusters(min_leaf_nodes=5)
    assert {m.qualname for m in cluster.members} == {"r.a", "r.b"}


def test_a_table_too_small_to_be_a_clone_is_not_one(tmp_path: Path):
    # Two entries each: `return frozenset({"&&", "||"})` in many grammars is not duplication.
    src = 'def a():\n    return frozenset({"&&", "||"})\n\ndef b():\n    return frozenset({"&&", "||"})\n'
    assert Structure.over(_module(tmp_path, src)).clone_clusters() == []


def _ctor(cls: str, fields: list[str], lang: str = "py") -> str:
    if lang == "py":
        body = "".join(f"        self._{f} = {f}\n" for f in fields)
        return f"class {cls}:\n    def __init__(self, {', '.join(fields)}):\n{body}\n"
    body = "".join(f"    this._{f} = {f};\n" for f in fields)
    return f"class {cls} {{\n  constructor({', '.join(fields)}) {{\n{body}  }}\n}}\n\n"


def _module_in(tmp_path: Path, filename: str, src: str):
    (tmp_path / filename).write_text(src)
    return scan_corpus(tmp_path, config=None).realms()[0].packages()[0].modules()[0]


def test_constructors_that_store_different_fields_are_not_clones(tmp_path: Path):
    src = _ctor("A", ["raw", "content", "path", "grammar"]) + _ctor("B", ["edges", "efferent", "afferent", "label"])
    assert Structure.over(_module(tmp_path, src)).clone_clusters(min_leaf_nodes=5) == []


def test_constructors_that_store_the_same_fields_are_clones(tmp_path: Path):
    # Same state, defined twice: that is duplication a parent class should hold.
    fields = ["raw", "content", "path", "grammar"]
    src = _ctor("A", fields) + _ctor("B", fields)
    [cluster] = Structure.over(_module(tmp_path, src)).clone_clusters(min_leaf_nodes=5)
    assert {m.qualname for m in cluster.members} == {"r.A.__init__", "r.B.__init__"}


def test_renamed_locals_and_parameters_are_still_clones(tmp_path: Path):
    # Only a stored member keeps its name; a local or a parameter is renameable.
    src = ("def a(p, q):\n    total = p + q\n    scaled = total * 2\n    if scaled > 9:\n        return scaled - 1\n    return scaled\n\n"
           "def b(x, y):\n    acc = x + y\n    out = acc * 2\n    if out > 9:\n        return out - 1\n    return out\n")
    [cluster] = Structure.over(_module(tmp_path, src)).clone_clusters(min_leaf_nodes=5)
    assert {m.qualname for m in cluster.members} == {"r.a", "r.b"}


def test_javascript_constructors_follow_the_same_rule(tmp_path: Path):
    same = ["raw", "content", "path", "grammar"]
    different = _ctor("A", same, "js") + _ctor("B", ["edges", "efferent", "afferent", "label"], "js")
    assert Structure.over(_module_in(tmp_path, "m.js", different)).clone_clusters(min_leaf_nodes=5) == []
    (tmp_path / "m.js").unlink()
    identical = _ctor("A", same, "js") + _ctor("B", same, "js")
    [cluster] = Structure.over(_module_in(tmp_path, "m.js", identical)).clone_clusters(min_leaf_nodes=5)
    assert len(cluster.members) == 2


def _reader(cls: str, members: tuple[str, str, str], local: str) -> str:
    a, b, c = members
    return (f"class {cls}:\n    def m(self):\n        {local} = self.{a}\n        x = self.{b} + self.{c}\n"
            f"        y = x * 2\n        if y > 9:\n            return y - {local}\n        return y\n\n")


def test_methods_that_read_different_members_are_different_code(tmp_path: Path):
    src = _reader("A", ("_p", "_q", "_r"), "v") + _reader("B", ("_a", "_b", "_c"), "v")
    assert Structure.over(_module(tmp_path, src)).clone_clusters(min_leaf_nodes=5) == []


def test_methods_that_read_the_same_members_through_renamed_locals_are_clones(tmp_path: Path):
    src = _reader("A", ("_p", "_q", "_r"), "v") + _reader("B", ("_p", "_q", "_r"), "w")
    [cluster] = Structure.over(_module(tmp_path, src)).clone_clusters(min_leaf_nodes=5)
    assert {m.qualname for m in cluster.members} == {"r.A.m", "r.B.m"}


def test_calling_a_different_function_or_keyword_is_different_code(tmp_path: Path):
    # The two dispatch lambdas that started this: same shape, different callee and keywords.
    src = ("def a(o):\n    return lexicon(o.root, o.out, scope=o.scope, top=o.top, kind=o.kind)\n\n"
           "def b(o):\n    return tree(o.root, o.out, scope=o.scope, depth=o.depth, kind=o.kind)\n")
    assert Structure.over(_module(tmp_path, src)).clone_clusters(min_leaf_nodes=5) == []


def test_renamed_loop_variables_and_tuple_targets_are_still_clones(tmp_path: Path):
    src = ("def a(rows):\n    total, n = 0, 0\n    for row in rows:\n        total = total + row\n        n = n + 1\n    return total / n\n\n"
           "def b(items):\n    acc, k = 0, 0\n    for it in items:\n        acc = acc + it\n        k = k + 1\n    return acc / k\n")
    [cluster] = Structure.over(_module(tmp_path, src)).clone_clusters(min_leaf_nodes=5)
    assert {m.qualname for m in cluster.members} == {"r.a", "r.b"}


def test_swapped_roles_of_bound_names_are_not_a_clone(tmp_path: Path):
    # Consistent renaming only: a body that uses its two parameters the other way round differs.
    src = ("def a(x, y):\n    z = x - y\n    w = z * x\n    return w + y + x\n\n"
           "def b(x, y):\n    z = y - x\n    w = z * y\n    return w + x + y\n")
    assert Structure.over(_module(tmp_path, src)).clone_clusters(min_leaf_nodes=5) == []


def test_renamed_parameters_locals_and_loop_variables_are_clones_in_javascript_too(tmp_path: Path):
    src = ("function a(xs) { let t = 0; for (const v of xs) { t = t + v * 2; } return t; }\n\n"
           "function b(ys) { let s = 0; for (const w of ys) { s = s + w * 2; } return s; }\n")
    (tmp_path / "m.js").write_text(src, encoding="utf-8")
    [cluster] = Structure.over(scan_corpus(tmp_path, config=None)).clone_clusters(min_leaf_nodes=5)
    assert {m.qualname for m in cluster.members} == {"m.a", "m.b"}


def test_the_receiver_of_a_stored_member_is_renameable(tmp_path: Path):
    # Only the member name is state; whether the receiver is called `self` or `node` is not.
    src = ("def a(self, p, q):\n    self._x = p\n    self._y = q\n    self._z = p + q\n    self._w = q - p\n\n"
           "def b(node, p, q):\n    node._x = p\n    node._y = q\n    node._z = p + q\n    node._w = q - p\n")
    [cluster] = Structure.over(_module(tmp_path, src)).clone_clusters(min_leaf_nodes=5)
    assert {m.qualname for m in cluster.members} == {"r.a", "r.b"}


def test_a_member_named_like_a_parameter_still_keeps_its_name(tmp_path: Path):
    # `self.a = a`: the member is state the class defines, even though a parameter shares its name.
    src = ("class A:\n    def __init__(self, a, b, c):\n        self.a = a\n        self.b = b\n        self.c = c\n\n"
           "class B:\n    def __init__(self, x, y, z):\n        self.x = x\n        self.y = y\n        self.z = z\n")
    assert Structure.over(_module(tmp_path, src)).clone_clusters(min_leaf_nodes=5) == []


def test_names_bound_outside_the_function_keep_their_text(tmp_path: Path):
    # A module constant is bound, but not by the function: reading LIMIT or OTHER is different code.
    body = "    total = n + {c}\n    scaled = total * 2\n    if scaled > {c}:\n        return scaled - 1\n    return scaled\n"
    src = "LIMIT = 9\nOTHER = 7\n\ndef a(n):\n" + body.format(c="LIMIT") + "\ndef b(n):\n" + body.format(c="OTHER")
    assert Structure.over(_module(tmp_path, src)).clone_clusters(min_leaf_nodes=5) == []


def test_functions_that_import_different_names_are_different_code(tmp_path: Path):
    # An imported name is bound by the body but names another module's entity: like a call to a
    # different function, it is not a renameable local.
    body = "    from pkg.extended import {n}\n    obj = {n}()\n    obj.prepare()\n    obj.run(1, 2)\n    return obj\n"
    src = "def a():\n" + body.format(n="Six") + "\ndef b():\n" + body.format(n="Seven") + "\ndef c():\n" + body.format(n="Six")
    [cluster] = Structure.over(_module(tmp_path, src)).clone_clusters(min_leaf_nodes=5)
    assert {m.qualname for m in cluster.members} == {"r.a", "r.c"}


@pytest.mark.parametrize("filename, src", [
    ("M.java", "class M {\n  int a(int p) { int total = p + 1; int out = total * 2; return out - total; }\n"
               "  int b(int q) { int acc = q + 1; int res = acc * 2; return res - acc; }\n}\n"),
    ("m.go", "package m\nfunc a(p int) int { total := p + 1; out := total * 2; return out - total }\n"
             "func b(q int) int { acc := q + 1; res := acc * 2; return res - acc }\n"),
])
def test_renamed_locals_are_clones_in_languages_that_declare_them(tmp_path: Path, filename, src):
    # Binding reads Java's and Go's declarations, so a renamed local no longer hides a clone.
    [cluster] = Structure.over(_module_in(tmp_path, filename, src)).clone_clusters(min_leaf_nodes=5)
    assert len(cluster.members) == 2
