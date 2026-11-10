"""rigid-package / useless-package — Martin (1994) package-zone violations.

Shared fixture: a 4-package corpus engineered so exactly one package lands in each
zone. ``core`` is concrete and depended-upon by everyone but depends on nothing
(I=0, A=0, D'=1.0 → Zone of Pain). ``lonely`` is all-abstract and depends on others
while nothing depends on it (I=1, A=1, D'=1.0 → Zone of Uselessness). ``a``/``b`` sit
on the main sequence and must stay silent.
"""
from __future__ import annotations

from pathlib import Path

from slop.config import RuleConfig
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
    assert rc.options == {"limit": 0.7}


def test_rigidity_registered():
    assert any(isinstance(r, RigidityRule) for r in RULE_REGISTRY)


def test_rigidity_fires_on_zone_of_pain(tmp_path: Path):
    pkgs = _packages(tmp_path)
    findings = list(RigidityRule().check(pkgs["core"], RigidityRule.default_config()))
    assert len(findings) == 1
    f = findings[0]
    assert f.rule == "rigid-package"
    assert f.path == str(tmp_path / "core")       # located at the package directory
    assert f.value == 1.0 and f.threshold == 0.7  # D' and its limit
    assert "Zone of Pain" in f.message
    assert "core" in f.message


def test_rigidity_silent_on_main_sequence(tmp_path: Path):
    pkgs = _packages(tmp_path)
    cfg = RigidityRule.default_config()
    for name in ("a", "b", "lonely"):
        assert list(RigidityRule().check(pkgs[name], cfg)) == []


def test_rigidity_strictly_greater_than_limit(tmp_path: Path):
    pkgs = _packages(tmp_path)
    # D' is 1.0: a limit equal to it is not exceeded, a limit just below it is.
    at = RuleConfig(name=RigidityRule.name, options={"limit": 1.0})
    below = RuleConfig(name=RigidityRule.name, options={"limit": 0.99})
    assert list(RigidityRule().check(pkgs["core"], at)) == []
    assert len(list(RigidityRule().check(pkgs["core"], below))) == 1


# ---- uselessness ----------------------------------------------------------

def test_uselessness_default_config():
    rc = UselessnessRule.default_config()
    assert UselessnessRule.altitudes == frozenset({ScopeKind.PACKAGE})
    assert rc.options == {"limit": 0.7}


def test_uselessness_registered():
    assert any(isinstance(r, UselessnessRule) for r in RULE_REGISTRY)


def test_uselessness_fires_on_zone_of_uselessness(tmp_path: Path):
    pkgs = _packages(tmp_path)
    findings = list(UselessnessRule().check(pkgs["lonely"], UselessnessRule.default_config()))
    assert len(findings) == 1
    f = findings[0]
    assert f.rule == "useless-package"
    assert f.path == str(tmp_path / "lonely")
    assert f.value == 1.0 and f.threshold == 0.7
    assert "Zone of Uselessness" in f.message
    assert "lonely" in f.message


def test_uselessness_silent_outside_zone(tmp_path: Path):
    pkgs = _packages(tmp_path)
    cfg = UselessnessRule.default_config()
    for name in ("a", "b", "core"):
        assert list(UselessnessRule().check(pkgs[name], cfg)) == []


def test_uselessness_strictly_greater_than_limit(tmp_path: Path):
    pkgs = _packages(tmp_path)
    at = RuleConfig(name=UselessnessRule.name, options={"limit": 1.0})
    below = RuleConfig(name=UselessnessRule.name, options={"limit": 0.99})
    assert list(UselessnessRule().check(pkgs["lonely"], at)) == []
    assert len(list(UselessnessRule().check(pkgs["lonely"], below))) == 1

