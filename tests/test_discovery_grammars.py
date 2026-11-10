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
