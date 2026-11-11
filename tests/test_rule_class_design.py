"""class-coupling / class-inheritance-depth / class-children / class-cohesion."""
from __future__ import annotations

from pathlib import Path

from slop.config import RuleConfig
from slop.metrics.structural.view import Structure
from slop.rules import RULE_REGISTRY
from slop.rules.class_design import (
    ChildrenRule,
    CohesionRule,
    CouplingRule,
    InheritanceDepthRule,
)
from slop.scope import scan_corpus
from slop.scope.identity import ScopeKind

# Base <- Mid <- Leaf; Leaf also uses Base: DIT(Leaf)=2, NOC(Base)=1, CBO(Leaf)=2.
SRC = '''\
class Base:
    pass

class Mid(Base):
    pass

class Leaf(Mid):
    def m(self):
        x = Base()
        return x
'''

# Two method groups sharing no instance member: {f, g} via self.a and {h} via self.b.
SPLIT = '''\
class Split:
    def f(self):
        return self.a

    def g(self):
        self.a = 1

    def h(self):
        return self.b
'''

COHESIVE = '''\
class Whole:
    def f(self):
        return self.a

    def g(self):
        self.a = 1
'''

JAVA = '''\
class Split {
    int a;
    int b;
    int f() { return a; }
    int h() { return b; }
}
'''


def _classes(tmp_path: Path, src: str = SRC, filename: str = "ck.py") -> dict:
    (tmp_path / filename).write_text(src)
    mod = scan_corpus(tmp_path, config=None).realms()[0].packages()[0].modules()[0]
    return {c.name: c for c in mod.children() if c.KIND.name == "CLASS"}


def _cfg(rule, limit) -> RuleConfig:
    return RuleConfig(name=rule.name, options={"limit": limit})


def _check(rule, cls, config):
    return list(rule().check(cls, config))


def test_registered():
    for rule in (CouplingRule, InheritanceDepthRule, ChildrenRule, CohesionRule):
        assert any(isinstance(r, rule) for r in RULE_REGISTRY)
        assert rule.altitudes == frozenset({ScopeKind.CLASS})


def test_default_limits_and_enablement():
    defaults = {
        CouplingRule: 8, InheritanceDepthRule: 4, ChildrenRule: 10, CohesionRule: 1,
    }
    for rule, limit in defaults.items():
        assert rule.default_config().options == {"limit": limit}
    for rule in (CouplingRule, InheritanceDepthRule, ChildrenRule, CohesionRule):
        assert rule.default_config().enabled is True
    assert CohesionRule.subjective and not CouplingRule.subjective


def test_inheritance_depth_fires_above_limit_only(tmp_path: Path):
    cs = _classes(tmp_path)
    assert _check(InheritanceDepthRule, cs["Leaf"], _cfg(InheritanceDepthRule, 2)) == []
    [v] = _check(InheritanceDepthRule, cs["Leaf"], _cfg(InheritanceDepthRule, 1))
    assert v.rule == "class-inheritance-depth"
    assert v.path == str(tmp_path / "ck.py")
    assert (v.line, v.column) == (7, 1)
    assert v.value == 2 and v.threshold == 1
    assert "Leaf" in v.message and "2" in v.message and "1" in v.message
    assert _check(InheritanceDepthRule, cs["Mid"], _cfg(InheritanceDepthRule, 1)) == []


def test_children_fires_above_limit_only(tmp_path: Path):
    cs = _classes(tmp_path)
    assert _check(ChildrenRule, cs["Base"], _cfg(ChildrenRule, 1)) == []
    [v] = _check(ChildrenRule, cs["Base"], _cfg(ChildrenRule, 0))
    assert v.rule == "class-children"
    assert (v.line, v.column) == (1, 1)
    assert v.value == 1 and v.threshold == 0
    assert "Base" in v.message
    # A class with no subclasses never exceeds a non-negative limit.
    assert _check(ChildrenRule, cs["Leaf"], _cfg(ChildrenRule, 0)) == []


def test_children_counts_direct_subclasses_only(tmp_path: Path):
    src = "class P:\n    pass\n\n" + "".join(f"class C{i}(P):\n    pass\n\n" for i in range(3)) \
        + "class G(C0):\n    pass\n"
    cs = _classes(tmp_path, src)
    [v] = _check(ChildrenRule, cs["P"], _cfg(ChildrenRule, 2))
    assert v.value == 3                  # G is a grandchild, not counted
    assert _check(ChildrenRule, cs["P"], _cfg(ChildrenRule, 3)) == []


def test_coupling_fires_above_limit_only(tmp_path: Path):
    cs = _classes(tmp_path)
    assert _check(CouplingRule, cs["Leaf"], _cfg(CouplingRule, 2)) == []
    [v] = _check(CouplingRule, cs["Leaf"], _cfg(CouplingRule, 1))
    assert v.rule == "class-coupling"
    assert (v.line, v.column) == (7, 1)
    assert v.value == 2 and v.threshold == 1
    assert "Leaf" in v.message


def test_defaults_are_silent_on_small_hierarchy(tmp_path: Path):
    cs = _classes(tmp_path)
    for rule in (CouplingRule, InheritanceDepthRule, ChildrenRule):
        for cls in cs.values():
            assert _check(rule, cls, rule.default_config()) == []



def test_cohesion_lists_method_groups(tmp_path: Path):
    cs = _classes(tmp_path, SPLIT)
    assert Structure.over(cs["Split"]).cohesion().lcom4 == 2
    [v] = _check(CohesionRule, cs["Split"], _cfg(CohesionRule, 1))
    assert v.rule == "class-cohesion"
    assert (v.line, v.column) == (1, 1)
    assert v.value == 2 and v.threshold == 1
    assert "{f, g}" in v.message and "{h}" in v.message


def test_cohesion_boundary_and_cohesive_class(tmp_path: Path):
    cs = _classes(tmp_path, SPLIT)
    assert _check(CohesionRule, cs["Split"], _cfg(CohesionRule, 2)) == []
    (tmp_path / "w").mkdir()
    whole = _classes(tmp_path / "w", COHESIVE)
    assert _check(CohesionRule, whole["Whole"], _cfg(CohesionRule, 1)) == []


def test_cohesion_silent_where_unmeasurable(tmp_path: Path):
    cs = _classes(tmp_path, JAVA, "Split.java")
    assert Structure.over(cs["Split"]).cohesion() is None
    assert _check(CohesionRule, cs["Split"], _cfg(CohesionRule, 0)) == []
