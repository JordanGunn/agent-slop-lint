"""class-shape rule — CK suite as a Class-altitude observation (no verdict).

Reuses the test_ck fixture: Base(dit0,noc1,cbo0), Mid(dit1,noc1,cbo1),
Leaf(dit2,noc0,cbo2). Asserts the attention-floors gate output and the finding is
a claim-free observation, never a verdict.
"""
from __future__ import annotations

from pathlib import Path

from slop.config import RuleConfig
from slop.finding import Action, Disposition, Severity
from slop.rules import RULE_REGISTRY
from slop.rules.class_shape import ClassShapeRule
from slop.scope import scan_corpus
from slop.scope.identity import ScopeKind

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


def _classes(tmp_path: Path) -> dict:
    (tmp_path / "ck.py").write_text(SRC)
    mod = scan_corpus(tmp_path, config=None).realms()[0].packages()[0].modules()[0]
    return {c.name: c for c in mod.children() if c.KIND is ScopeKind.CLASS}


def test_default_config_is_class_altitude_observation():
    rc = ClassShapeRule.default_config()
    assert rc.severity is Severity.INFO
    assert rc.param("cbo_attention") == 8
    assert rc.param("dit_attention") == 4
    assert rc.param("noc_attention") == 10
    assert ClassShapeRule.altitudes == frozenset({ScopeKind.CLASS})


def test_registered():
    assert any(isinstance(r, ClassShapeRule) for r in RULE_REGISTRY)


def test_silent_within_default_attention_floors(tmp_path: Path):
    cs = _classes(tmp_path)
    rule, cfg = ClassShapeRule(), ClassShapeRule.default_config()
    # Tiny hierarchy: every class is far under 8/4/10 — no observation.
    assert all(list(rule.check(c, cfg)) == [] for c in cs.values())


def test_emits_observation_when_notable(tmp_path: Path):
    cs = _classes(tmp_path)
    # Lower the DIT floor so Leaf (dit 2) becomes notable; keep CBO/NOC high.
    cfg = RuleConfig(name=ClassShapeRule.name, severity=Severity.INFO,
                     params={"cbo_attention": 8, "dit_attention": 1, "noc_attention": 10})
    findings = list(ClassShapeRule().check(cs["Leaf"], cfg))
    assert len(findings) == 1
    f = findings[0]
    assert f.disposition is Disposition.OBSERVATION
    assert f.action is Action.INVESTIGATE       # observation terminal, never a verdict
    assert f.severity is Severity.INFO           # pinned; cannot gate the build
    assert f.evidence.kind == "ck-profile"
    assert f.evidence.data["dit"] == 2 and f.evidence.data["cbo"] == 2
    assert "inheritance depth 2" in f.message and "Leaf" in f.message


def test_noc_is_framed_as_ambiguous(tmp_path: Path):
    cs = _classes(tmp_path)
    # Drop the NOC floor so Base (noc 1) is notable; the prose must not call it a defect.
    cfg = RuleConfig(name=ClassShapeRule.name,
                     params={"cbo_attention": 8, "dit_attention": 4, "noc_attention": 0})
    findings = list(ClassShapeRule().check(cs["Base"], cfg))
    assert len(findings) == 1
    assert "healthy abstraction" in findings[0].message
