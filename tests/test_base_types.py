"""A class's bases are the classes its heritage clause names: a generic by its head (``List<T>``
is ``List``), a qualified name by its last segment (``ns.Q`` is ``Q``), and an interface's
``extends`` as well as a class's. A base that is an expression (a mixin call) names no class."""
from __future__ import annotations

from pathlib import Path

import pytest

from slop.ast import GRAMMARS_BY_ID
from slop.ast.parse import detect_language
from slop.ast.tree import AST
from slop.scope import scan_corpus
from slop.scope.find import walk
from slop.scope.identity import ScopeKind

_CASES = [
    ("X.java", "interface A extends B, C<T> {}", "A", ("B", "C")),
    ("X.java", "class D extends E<T> implements F, G<T> {}", "D", ("E", "F", "G")),
    ("X.java", "class H extends p.Q implements r.S {}", "H", ("Q", "S")),
    ("x.ts", "interface A extends B, C<T> {}", "A", ("B", "C")),
    ("x.ts", "class D extends E<T> implements F, G<T> {}", "D", ("E", "F", "G")),
    ("x.ts", "class H extends ns.Q implements ns.S {}", "H", ("Q", "S")),
    ("x.ts", "class K extends mixin(B) {}", "K", ()),
    ("y.js", "class C extends ns.D {}", "C", ("D",)),
    ("x.cs", "interface IA : IB, IC<T> {}", "IA", ("IB", "IC")),
    ("x.cs", "class D : E<T>, IF {}", "D", ("E", "IF")),
    ("x.cs", "class H : N.Q {}", "H", ("Q",)),
    ("v.cpp", "struct C : public ns::D, private E<int> {};", "C", ("D", "E")),
    ("t.py", "class R(Store[int], pkg.mod.Base, metaclass=M): pass", "R", ("Store", "Base")),
    ("w.rb", "class C < Mod::D; end", "C", ("D",)),
    ("u.jl", "struct B{T} <: Mod.Shape end", "B", ("Shape",)),
    ("u.jl", "struct C <: Box{Int} end", "C", ("Box",)),
]


@pytest.mark.parametrize("file,source,name,bases", _CASES, ids=[f"{c[0]}:{c[2]}:{i}" for i, c in enumerate(_CASES)])
def test_bases_are_the_classes_the_heritage_clause_names(tmp_path: Path, file, source, name, bases):
    path = tmp_path / file
    path.write_text(source + "\n", encoding="utf-8")
    grammar = GRAMMARS_BY_ID[detect_language(path)]
    content = path.read_bytes()

    def nodes(node):
        yield node
        for child in node.children():
            yield from nodes(child)

    [cls] = [n for n in nodes(AST.parse(path, grammar).root)
             if n.type in grammar.classes() and grammar.extract_name(n.raw, content) == name]
    assert tuple(grammar.extract_superclasses(cls.raw, content)) == bases


def test_a_base_name_never_resolves_to_a_class_in_another_language(tmp_path: Path):
    (tmp_path / "s.rs").write_text("struct S { a: i32 }\n", encoding="utf-8")
    (tmp_path / "h.ts").write_text("class Base {}\nclass H extends S {}\nclass K extends Base {}\n", encoding="utf-8")
    classes = {s.qualname: s for s in walk(scan_corpus(tmp_path, config=None)) if s.id.kind is ScopeKind.CLASS}
    assert classes["h.H"].bases() == ()                      # S exists only in Rust
    assert [b.qualname for b in classes["h.K"].bases()] == ["h.Base"]   # same language still resolves
