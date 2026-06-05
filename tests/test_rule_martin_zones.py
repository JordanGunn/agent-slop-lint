"""structure.rigidity / structure.uselessness — Martin (1994) package-zone REVIEW verdicts.

Shared fixture: a 4-package corpus engineered so exactly one package lands in each
zone. ``core`` is concrete and depended-upon by everyone but depends on nothing
(I=0, A=0, D'=1.0 → Zone of Pain). ``lonely`` is all-abstract and depends on others
while nothing depends on it (I=1, A=1, D'=1.0 → Zone of Uselessness). ``a``/``b`` sit
on the main sequence and must stay silent.
"""
from __future__ import annotations

from pathlib import Path

from slop.config import RuleConfig
from slop.finding import Action, Disposition, Severity
from slop.rules import RULE_REGISTRY
from slop.rules.rigidity import RigidityRule
from slop.rules.uselessness import UselessnessRule
from slop.scope import scan_corpus
from slop.scope.identity import ScopeKind


def _packages(tmp_path: Path) -> dict:
    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "__init__.py").write_text("")
    (tmp_path / "core" / "thing.py").write_text("class Impl:\n    pass\n")
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "__init__.py").write_text("")
    (tmp_path / "a" / "mod.py").write_text("import core.thing\n")
    (tmp_path / "b").mkdir()
    (tmp_path / "b" / "__init__.py").write_text("")
    (tmp_path / "b" / "mod.py").write_text("from core import thing\n")
    (tmp_path / "lonely").mkdir()
    (tmp_path / "lonely" / "__init__.py").write_text("")
    (tmp_path / "lonely" / "iface.py").write_text(
        "from abc import ABC, abstractmethod\n"
        "import core.thing\nimport a.mod\n"
        "class IFace(ABC):\n    @abstractmethod\n    def go(self): ...\n"
    )
    corpus = scan_corpus(tmp_path, config=None)
    return {p.name: p for p in corpus.realms()[0].packages()}


# ---- rigidity -------------------------------------------------------------

def test_rigidity_default_config():
    rc = RigidityRule.default_config()
    assert RigidityRule.altitudes == frozenset({ScopeKind.PACKAGE})
    assert rc.threshold_for(ScopeKind.PACKAGE) == 0.7


def test_rigidity_registered():
    assert any(isinstance(r, RigidityRule) for r in RULE_REGISTRY)


def test_rigidity_fires_on_zone_of_pain(tmp_path: Path):
    pkgs = _packages(tmp_path)
    findings = list(RigidityRule().check(pkgs["core"], RigidityRule.default_config()))
    assert len(findings) == 1
    f = findings[0]
    assert f.disposition is Disposition.VERDICT
    assert f.action is Action.REVIEW
    assert f.severity is Severity.WARNING        # REVIEW caps at WARNING
    assert f.value == 1.0                          # D'
    assert "Zone of Pain" in f.prescription


def test_rigidity_silent_on_main_sequence(tmp_path: Path):
    pkgs = _packages(tmp_path)
    cfg = RigidityRule.default_config()
    for name in ("a", "b", "lonely"):
        assert list(RigidityRule().check(pkgs[name], cfg)) == []


def test_rigidity_depth_gate_silences_below_threshold(tmp_path: Path):
    pkgs = _packages(tmp_path)
    # D' is 1.0; a threshold above that silences even the in-zone package.
    cfg = RuleConfig(name=RigidityRule.name, thresholds={ScopeKind.PACKAGE.value: 1.0})
    assert list(RigidityRule().check(pkgs["core"], cfg)) == []


# ---- uselessness ----------------------------------------------------------

def test_uselessness_default_config():
    rc = UselessnessRule.default_config()
    assert UselessnessRule.altitudes == frozenset({ScopeKind.PACKAGE})
    assert rc.threshold_for(ScopeKind.PACKAGE) == 0.7


def test_uselessness_registered():
    assert any(isinstance(r, UselessnessRule) for r in RULE_REGISTRY)


def test_uselessness_fires_on_zone_of_uselessness(tmp_path: Path):
    pkgs = _packages(tmp_path)
    findings = list(UselessnessRule().check(pkgs["lonely"], UselessnessRule.default_config()))
    assert len(findings) == 1
    f = findings[0]
    assert f.disposition is Disposition.VERDICT
    assert f.action is Action.REVIEW
    assert f.severity is Severity.WARNING
    assert "Zone of Uselessness" in f.prescription


def test_uselessness_silent_outside_zone(tmp_path: Path):
    pkgs = _packages(tmp_path)
    cfg = UselessnessRule.default_config()
    for name in ("a", "b", "core"):
        assert list(UselessnessRule().check(pkgs[name], cfg)) == []
