"""The properties a class declares: class-body fields and members assigned through the instance."""
from __future__ import annotations

from pathlib import Path

import pytest

from slop.lexical import coverage
from slop.lexicon import Role
from slop.ontology import Scheme, Term
from slop.scope import scan_corpus
from slop.scope.find import walk
from slop.scope.lexicon import build_declared_lexicon, declared_units


def _props(tmp_path: Path, name: str, source: str, cls: str = "A") -> tuple[str, ...]:
    (tmp_path / name).write_text(source)
    corpus = scan_corpus(tmp_path, config=None)
    return next(c for c in corpus._iter_classes() if c.name == cls).properties()


def test_python_properties_are_fields_plus_members_assigned_through_self(tmp_path: Path):
    src = (
        "class A:\n"
        "    x: int = 1\n"
        "    y: str\n"
        "    z = 2\n"
        "    __slots__ = ()\n"
        "    def __init__(self):\n"
        "        self.w = 1\n"
        "        self.x = 5\n"
        "    def f(self, other):\n"
        "        self.v += 2\n"
        "        other.q = 1\n"
        "        copy = self.fetched\n"
        "        return self.read\n"
    )
    # Class-body fields first, then assigned members; a name once; no dunder, no other
    # object's attribute, and a member that is only read (`self.read`, or `self.fetched` on
    # the right of an assignment) or only updated (`self.v += 2`) is not declared.
    assert _props(tmp_path, "m.py", src) == ("x", "y", "z", "w")


def test_an_augmented_assignment_alone_declares_nothing_but_does_not_hide_a_declaration(tmp_path: Path):
    src = (
        "class A:\n"
        "    def f(self):\n"
        "        self.updated_only += 1\n"
        "        self.declared = 0\n"
        "        self.declared += 1\n"
    )
    assert _props(tmp_path, "m.py", src) == ("declared",)


def test_typescript_properties(tmp_path: Path):
    ts = ("class A {\n  x: number = 1;\n  private y = 2;\n  constructor() { this.w = 1 }\n"
          "  f() { this.v += 1; return this.readonly }\n}\n")
    assert _props(tmp_path, "m.ts", ts) == ("x", "y", "w")


def test_javascript_properties(tmp_path: Path):
    js = "class A {\n  x = 1;\n  constructor() { this.w = 1 }\n}\n"
    assert _props(tmp_path, "m.js", js) == ("x", "w")


def test_a_static_method_assigning_through_its_first_parameter_declares_nothing(tmp_path: Path):
    src = "class A:\n    @classmethod\n    def make(cls):\n        cls.registry = {}\n"
    assert _props(tmp_path, "m.py", src) == ()


@pytest.mark.parametrize("name, src, cls, props", [
    ("A.java", "class A { int x; String y; void f() { int z = 1; } class B { int w; } }", "A", ("x", "y")),
    ("A.cs", "class A { int x; public string Name { get; set; } }", "A", ("x", "Name")),
    ("a.cpp", "class A { int x; double y; void f() {} };", "A", ("x", "y")),
    ("a.go", "package p\ntype A struct { x int; y string }\n", "A", ("x", "y")),
    ("a.rs", "struct A { x: i32, y: String }\n", "A", ("x", "y")),
    ("a.rb", "class A\n  def initialize\n    @x = 1\n    @y ||= 2\n  end\n  def f\n    @x += @z\n  end\nend\n",
     "A", ("@x", "@y")),
    ("a.jl", "struct A\n  x::Int\n  y\nend\n", "A", ("x", "y")),
])
def test_declared_fields_are_properties_in_every_language(tmp_path: Path, name, src, cls, props):
    # A local is not a field, nor is a nested class's field. Ruby's `@y ||= 2` sets `@y` when it
    # is unset, so it declares it.
    assert _props(tmp_path, name, src, cls) == props


def test_properties_enter_the_declared_lexicon_with_their_own_role(tmp_path: Path):
    (tmp_path / "m.py").write_text("class Ticket:\n    def __init__(self):\n        self.escalation = None\n")
    corpus = scan_corpus(tmp_path, config=None)
    assert ("escalation", Role.PROPERTY) in {(t, r) for s in walk(corpus) for t, r, _span in declared_units(s)}


def test_a_property_named_like_a_vocabulary_word_is_covered(tmp_path: Path):
    # `status` is never a parameter or a function name here; only the property declares it.
    (tmp_path / "m.py").write_text("class Ticket:\n    def __init__(self):\n        self.status = 'open'\n")
    declared = build_declared_lexicon(scan_corpus(tmp_path, config=None))
    result = coverage(declared, Scheme("desk", [Term("Status", "Where a ticket is in its life.")]))
    assert "status" in {o.token for o in result.covered}
