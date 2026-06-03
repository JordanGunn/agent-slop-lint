"""structure.dependency-cycles — one ERROR verdict per import cycle (ADP, Martin 2002).

Fixture mirrors test_dependency: a.py <-> b.py is a 2-module cycle; a single acyclic
edge is clean.
"""
from __future__ import annotations

from pathlib import Path

from slop.config import RuleConfig
from slop.finding import Action, Disposition, Severity
from slop.rules import RULE_REGISTRY
from slop.rules.dependency_cycles import DependencyCyclesRule
from slop.scope import scan_corpus
from slop.scope.identity import ScopeKind


def _corpus(tmp_path: Path, cyclic: bool):
    (tmp_path / "a.py").write_text("import b\n")
    (tmp_path / "b.py").write_text("import a\n" if cyclic else "x = 1\n")
    return scan_corpus(tmp_path, config=None)


def test_default_config_is_corpus_error():
    rc = DependencyCyclesRule.default_config()
    assert DependencyCyclesRule.altitudes == frozenset({ScopeKind.CORPUS})
    assert rc.severity is Severity.ERROR


def test_registered():
    assert any(isinstance(r, DependencyCyclesRule) for r in RULE_REGISTRY)


def test_fires_on_cycle(tmp_path: Path):
    corpus = _corpus(tmp_path, cyclic=True)
    findings = list(DependencyCyclesRule().check(corpus, DependencyCyclesRule.default_config()))
    assert len(findings) == 1
    f = findings[0]
    assert f.disposition is Disposition.VERDICT
    assert f.action is Action.BREAK_DEPENDENCY_CYCLE
    assert f.severity is Severity.ERROR              # cycles fail the build
    assert f.value == 2
    assert sorted(f.metadata["cycle"]) == ["a", "b"]
    assert "a" in f.message and "b" in f.message


def test_silent_without_cycle(tmp_path: Path):
    corpus = _corpus(tmp_path, cyclic=False)
    assert list(DependencyCyclesRule().check(corpus, DependencyCyclesRule.default_config())) == []


def test_severity_is_tunable(tmp_path: Path):
    corpus = _corpus(tmp_path, cyclic=True)
    cfg = RuleConfig(name=DependencyCyclesRule.name, severity=Severity.WARNING)
    f = list(DependencyCyclesRule().check(corpus, cfg))[0]
    assert f.severity is Severity.WARNING            # tunable down off the ERROR default
