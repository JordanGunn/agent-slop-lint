"""LCOM4: groups of methods joined through shared instance members."""
from __future__ import annotations

from pathlib import Path

import pytest

from slop.metrics.structural.view import Structure
from slop.scope import scan_corpus


def _cohesion(tmp_path: Path, name: str, source: str, cls: str = "A"):
    (tmp_path / name).write_text(source)
    module = scan_corpus(tmp_path, config=None).realms()[0].packages()[0].modules()[0]
    target = next(c for c in module.children() if c.KIND.name == "CLASS" and c.name == cls)
    return Structure.over(target).cohesion()


def _groups(tmp_path: Path, name: str, source: str, cls: str = "A"):
    c = _cohesion(tmp_path, name, source, cls)
    return None if c is None else c.groups


def test_independent_attribute_clusters_are_separate_groups(tmp_path: Path):
    src = (
        "class A:\n"
        "    def get_a(self): return self.a\n"
        "    def set_a(self, v): self.a = v\n"
        "    def get_b(self): return self.b\n"
        "    def set_b(self, v): self.b = v\n"
    )
    assert _groups(tmp_path, "m.py", src) == (("get_a", "set_a"), ("get_b", "set_b"))


def test_a_call_through_self_joins_methods(tmp_path: Path):
    src = (
        "class A:\n"
        "    def run(self): return self.step()\n"
        "    def step(self): return 1\n"
        "    def other(self): return self.z\n"
    )
    assert _groups(tmp_path, "m.py", src) == (("run", "step"), ("other",))


def test_constructor_does_not_join_everything(tmp_path: Path):
    src = (
        "class A:\n"
        "    def __init__(self):\n"
        "        self.a = 1\n"
        "        self.b = 2\n"
        "    def use_a(self): return self.a\n"
        "    def use_b(self): return self.b\n"
    )
    assert _groups(tmp_path, "m.py", src) == (("use_a",), ("use_b",))


def test_static_and_class_methods_have_no_instance_and_are_left_out(tmp_path: Path):
    src = (
        "class A:\n"
        "    def f(self): return self.x\n"
        "    @staticmethod\n"
        "    def s(): return 1\n"
        "    @classmethod\n"
        "    def c(cls): return cls.x\n"
    )
    assert _groups(tmp_path, "m.py", src) == (("f",),)


def test_a_closure_inside_a_method_counts_toward_that_method(tmp_path: Path):
    src = (
        "class A:\n"
        "    def f(self):\n"
        "        return lambda: self.shared\n"
        "    def g(self): return self.shared\n"
    )
    assert _groups(tmp_path, "m.py", src) == (("f", "g"),)


def test_property_setter_redefinition_is_one_method(tmp_path: Path):
    src = (
        "class A:\n"
        "    @property\n"
        "    def v(self): return self._v\n"
        "    @v.setter\n"
        "    def v(self, x): self._v = x\n"
    )
    assert _groups(tmp_path, "m.py", src) == (("v",),)


def test_a_non_self_receiver_is_not_an_instance_member(tmp_path: Path):
    src = (
        "class A:\n"
        "    def f(self, other): return other.x\n"
        "    def g(self, other): return other.x\n"
    )
    c = _cohesion(tmp_path, "m.py", src)
    assert (c.groups, c.detached) == ((), ("f", "g"))


def test_typescript_this_members_and_static(tmp_path: Path):
    src = (
        "class A {\n"
        "  constructor() { this.a = 1; this.b = 2 }\n"
        "  static make() { return new A() }\n"
        "  getA() { return this.a }\n"
        "  setA(v) { this.a = v }\n"
        "  getB() { return this.b }\n"
        "}\n"
    )
    assert _groups(tmp_path, "m.ts", src) == (("getA", "setA"), ("getB",))


def test_javascript_method_call_through_this_joins(tmp_path: Path):
    src = "class A {\n  run() { return this.step() }\n  step() { return 1 }\n}\n"
    assert _groups(tmp_path, "m.js", src) == (("run", "step"),)


@pytest.mark.parametrize("name, src", [
    ("A.java", "class A { int x; int f() { return x; } int g() { return this.x; } }"),
    ("A.cs", "class A { int x; int F() { return x; } }"),
])
def test_languages_with_implicit_this_are_unmeasurable_not_zero(tmp_path: Path, name: str, src: str):
    # A bare `x` means `this.x` there; counting only explicit `this.` would invent splits.
    assert _groups(tmp_path, name, src) is None


def test_class_shape_narrates_the_groups(tmp_path: Path):
    from slop.rules.class_shape import ClassShapeRule
    (tmp_path / "m.py").write_text(
        "class A:\n"
        "    def f(self): return self.a\n"
        "    def g(self): return self.b\n"
    )
    module = scan_corpus(tmp_path, config=None).realms()[0].packages()[0].modules()[0]
    cls = next(c for c in module.children() if c.KIND.name == "CLASS")
    [obs] = list(ClassShapeRule().check(cls, ClassShapeRule.default_config()))
    assert obs.evidence.data["lcom4"] == 2
    assert obs.evidence.data["method_groups"] == [["f"], ["g"]]
    assert "{f}; {g}" in obs.message


def test_methods_reaching_no_instance_state_are_detached_not_groups(tmp_path: Path):
    # An interface or an enum-like class: nothing to share, so nothing to split.
    src = (
        "class A:\n"
        "    def save(self): raise NotImplementedError\n"
        "    def load(self): raise NotImplementedError\n"
        "    @property\n"
        "    def code(self): return 7\n"
    )
    c = _cohesion(tmp_path, "m.py", src)
    assert (c.groups, c.detached, c.lcom4) == ((), ("save", "load", "code"), 0)


def test_a_callee_that_touches_no_state_is_attached_to_its_caller(tmp_path: Path):
    src = (
        "class A:\n"
        "    def run(self): return self.step()\n"
        "    def step(self): return 1\n"
    )
    c = _cohesion(tmp_path, "m.py", src)
    assert (c.groups, c.detached) == ((("run", "step"),), ())


def test_class_shape_is_silent_for_a_class_with_only_detached_methods(tmp_path: Path):
    from slop.rules.class_shape import ClassShapeRule
    (tmp_path / "m.py").write_text(
        "class A:\n"
        "    def save(self): raise NotImplementedError\n"
        "    def load(self): raise NotImplementedError\n"
    )
    module = scan_corpus(tmp_path, config=None).realms()[0].packages()[0].modules()[0]
    cls = next(c for c in module.children() if c.KIND.name == "CLASS")
    assert list(ClassShapeRule().check(cls, ClassShapeRule.default_config())) == []


def test_class_field_arrow_functions_are_distinct_methods(tmp_path: Path):
    # Unnamed callables must not share one node: `handler` and `other` touch different
    # members, so they are two groups, and each is named by where it is declared.
    src = (
        "class A {\n"
        "  x = 1;\n"
        "  handler = () => this.x;\n"
        "  other = () => this.y;\n"
        "  third() { return this.x }\n"
        "}\n"
    )
    groups = _groups(tmp_path, "m.ts", src)
    assert [g[-1] for g in groups] == ["third", "<anonymous>:4"]
    assert groups[0][0].startswith("<anonymous>:3")


def test_a_class_with_no_methods_has_nothing_measured_not_perfect_cohesion(tmp_path: Path):
    c = _cohesion(tmp_path, "m.py", "class A:\n    x = 1\n")
    assert (c.groups, c.detached, c.lcom4) == ((), (), 0)
