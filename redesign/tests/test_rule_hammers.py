"""lexical.hammers — institutionalised catch-all vocabulary as an observation."""
from __future__ import annotations

from pathlib import Path

from slop.finding import Action, Disposition, Severity
from slop.rules import RULE_REGISTRY
from slop.rules.hammers import HammersRule
from slop.scope import scan_corpus
from slop.scope.identity import ScopeKind


def test_default_config():
    rc = HammersRule.default_config()
    assert HammersRule.altitudes == frozenset({ScopeKind.CORPUS})
    assert rc.param("min_spread") == 3


def test_registered():
    assert any(isinstance(r, HammersRule) for r in RULE_REGISTRY)


def test_emits_observation_for_institutionalised_term(tmp_path: Path):
    # 'manager' recurs across 3 files, each bonded to a different concept → isolate.
    (tmp_path / "a.py").write_text("class UserManager:\n    def act(self): pass\n")
    (tmp_path / "b.py").write_text("class OrderManager:\n    def act(self): pass\n")
    (tmp_path / "c.py").write_text("class PaymentManager:\n    def act(self): pass\n")
    corpus = scan_corpus(tmp_path, config=None)
    findings = list(HammersRule().check(corpus, HammersRule.default_config()))
    assert len(findings) == 1
    f = findings[0]
    assert f.disposition is Disposition.OBSERVATION
    assert f.action is Action.INVESTIGATE
    assert f.severity is Severity.INFO
    assert f.evidence.data["term"] == "manager"
    assert f.evidence.data["file_spread"] == 3


def test_single_use_hammer_is_not_institutionalised(tmp_path: Path):
    # One Manager in one file is a style nit, not systemic — not surfaced.
    (tmp_path / "a.py").write_text("class UserManager:\n    def act(self): pass\n")
    corpus = scan_corpus(tmp_path, config=None)
    assert list(HammersRule().check(corpus, HammersRule.default_config())) == []
