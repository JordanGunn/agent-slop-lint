"""Named type definitions are discovered per grammar, and nothing phantom is invented.

Each case is a bug the primitives had: enums missing in Java/C#/TypeScript, Go named types
(and aliases) coming out as ``<anonymous>``, and Ruby's empty-bodied classes sprouting a
phantom ``<anonymous>`` child because the ``class`` keyword token shares its node type with
the ``class`` node.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from slop.scope import scan_corpus
from slop.scope.find import collisions, find
from slop.scope.identity import ScopeKind


def _names(tmp_path: Path, kind: ScopeKind) -> set[str]:
    return {m.name for m in find(scan_corpus(tmp_path, config=None), kind=kind)}


@pytest.mark.parametrize("filename,source,expected", [
    ("Status.java", "public enum Status { OPEN }\npublic interface Shape {}\n", {"Status", "Shape"}),
    ("m.ts", "export enum Status { Open }\nexport interface Shape {}\n", {"Status", "Shape"}),
    ("m.rs", "pub enum Status { Open }\npub trait Shape {}\n", {"Status", "Shape"}),
    ("m.py", "import enum\nclass Status(enum.Enum):\n    OPEN = 1\n", {"Status"}),
])
def test_enums_and_interfaces_are_discovered(tmp_path: Path, filename, source, expected):
    (tmp_path / filename).write_text(source)
    assert _names(tmp_path, ScopeKind.CLASS) == expected


def test_csharp_discovers_the_constructs_a_real_file_uses(tmp_path: Path):
    # A namespace, a generic class with a property, an interface, a struct and an enum.
    (tmp_path / "Order.cs").write_text(
        "using System.Collections.Generic;\n"
        "namespace Shop.Orders {\n"
        "    public class Repository<T> where T : class {\n"
        "        private readonly List<T> items = new List<T>();\n"
        "        public int Count { get { return items.Count; } }\n"
        "        public void Add(T item) { items.Add(item); }\n"
        "    }\n"
        "    public interface IPricing { decimal Total(int qty); }\n"
        "    public struct Money { public decimal Amount; }\n"
        "    public enum Status { Open, Closed }\n"
        "}\n"
    )
    assert _names(tmp_path, ScopeKind.CLASS) == {"Repository", "IPricing", "Money", "Status"}
    assert {"Add", "Total"} <= _names(tmp_path, ScopeKind.CALLABLE)


def test_go_names_every_declared_type_not_only_structs_and_interfaces(tmp_path: Path):
    (tmp_path / "go.mod").write_text("module example.com/m\ngo 1.21\n")
    (tmp_path / "m.go").write_text(
        "package m\n\ntype Shape interface{}\ntype Alias = int\ntype Status int\n"
        "type Point struct{ X int }\n"
    )
    names = _names(tmp_path, ScopeKind.CLASS)
    assert names == {"Shape", "Alias", "Status", "Point"}
    assert "<anonymous>" not in names


def test_ruby_empty_classes_do_not_grow_a_phantom_child(tmp_path: Path):
    (tmp_path / "m.rb").write_text(
        "module Shop\n  class Order\n    def total\n      1\n    end\n  end\n\n"
        "  class Customer\n  end\nend\n\nclass Top\nend\n"
    )
    names = {m.name for m in find(scan_corpus(tmp_path, config=None), kind=ScopeKind.CLASS)}
    assert names == {"Shop", "Order", "Customer", "Top"}
    assert not collisions(scan_corpus(tmp_path, config=None))


# ---- C: a specifier is a definition only when it has a body ----------------

_C_SOURCE = (
    "struct Node;                         /* forward declaration: not a definition */\n"
    "struct Node { int v; struct Node *next; };   /* definition, with a self-reference */\n"
    "typedef struct { int x; int y; } Point;      /* anonymous: named by its typedef */\n"
    "typedef struct Tag { int a; } Alias_t;       /* tagged: the tag is the name */\n"
    "enum Color { RED, GREEN };\n"
    "union Value { int i; float f; };\n"
    "struct Node *head;                   /* file-scope usage: not a definition */\n"
    "int run(struct Node *n) { return n->v; }\n"
)


def test_c_defines_a_type_only_where_the_specifier_has_a_body(tmp_path: Path):
    (tmp_path / "m.c").write_text(_C_SOURCE)
    corpus = scan_corpus(tmp_path, config=None)
    classes = find(corpus, kind=ScopeKind.CLASS)
    assert sorted(m.name for m in classes) == ["Color", "Node", "Point", "Tag", "Value"]
    assert [m.line for m in classes if m.name == "Node"] == [2]   # the definition, once
    assert not collisions(corpus)                                  # usages are not phantoms
    assert {m.name for m in find(corpus, kind=ScopeKind.CALLABLE)} == {"run"}


def test_c_names_an_anonymous_struct_from_its_typedef_not_as_anonymous(tmp_path: Path):
    (tmp_path / "m.c").write_text("typedef struct { int x; } Point;\n")
    assert _names(tmp_path, ScopeKind.CLASS) == {"Point"}


# ---- Julia: struct, abstract and parametric types, with their supertypes ----

def test_julia_discovers_struct_abstract_and_parametric_types(tmp_path: Path):
    (tmp_path / "m.jl").write_text(
        "abstract type Shape end\n\nstruct Circle <: Shape\n    r::Float64\nend\n\n"
        "mutable struct Box{T}\n    x::T\nend\n\nstruct Plain\nend\n"
    )
    corpus = scan_corpus(tmp_path, config=None)
    assert {m.name for m in find(corpus, kind=ScopeKind.CLASS)} == {"Shape", "Circle", "Box", "Plain"}
    by_name = {c.name: c for c in corpus._iter_classes()}
    assert by_name["Circle"]._base_names == ("Shape",)       # struct Circle <: Shape
    assert by_name["Shape"].is_abstract and not by_name["Circle"].is_abstract
    assert by_name["Box"]._base_names == ()                  # Box{T} is named Box, no supertype
