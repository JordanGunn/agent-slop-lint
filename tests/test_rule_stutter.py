"""lexical.stutter — a name restating its enclosing scope (verdict)."""
from __future__ import annotations

from pathlib import Path

from slop.finding import Action, Disposition, Severity
from slop.rules import RULE_REGISTRY
from slop.rules.stutter import StutterRule
from slop.scope import scan_corpus
from slop.scope.identity import ScopeKind

SRC = '''\
class UserManager:
    def get_user_id(self):
        return 1
    def reset(self):
        return 0
'''


def _corpus(tmp_path: Path):
    (tmp_path / "m.py").write_text(SRC)
    return scan_corpus(tmp_path, config=None)


def test_default_config():
    rc = StutterRule.default_config()
    assert StutterRule.altitudes == frozenset({ScopeKind.CORPUS})
    assert rc.param("min_overlap_tokens") == 1


def test_registered():
    assert any(isinstance(r, StutterRule) for r in RULE_REGISTRY)


def test_fires_when_name_restates_scope(tmp_path: Path):
    findings = list(StutterRule().check(_corpus(tmp_path), StutterRule.default_config()))
    # get_user_id restates UserManager via 'user'
    stutters = [f for f in findings if f.metadata["name"] == "get_user_id"]
    assert len(stutters) == 1
    f = stutters[0]
    assert f.disposition is Disposition.VERDICT
    assert f.action is Action.DROP_REDUNDANT_TOKENS
    assert f.severity is Severity.WARNING
    assert f.metadata["shared"] == ["user"]
    assert f.metadata["enclosing"] == "UserManager"


def test_non_restating_name_is_silent(tmp_path: Path):
    findings = list(StutterRule().check(_corpus(tmp_path), StutterRule.default_config()))
    assert all(f.metadata["name"] != "reset" for f in findings)
