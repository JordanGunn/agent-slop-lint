"""structure.sentinels — stringly-typed sentinel parameter, directed WARNING verdict."""
from __future__ import annotations

from pathlib import Path

from slop.finding import Action, Disposition, Severity
from slop.rules import RULE_REGISTRY
from slop.rules.sentinels import SentinelsRule
from slop.scope import scan_corpus
from slop.scope.identity import ScopeKind

SRC = '''\
def open_file(mode: str):
    return mode

def plain(count: int):
    return count
'''


def _callables(tmp_path: Path) -> dict:
    (tmp_path / "m.py").write_text(SRC)
    corpus = scan_corpus(tmp_path, config=None)

    def walk(s):
        yield s
        for c in s.children():
            yield from walk(c)

    return {c.name: c for c in walk(corpus) if c.KIND is ScopeKind.CALLABLE}


def test_default_config():
    rc = SentinelsRule.default_config()
    assert SentinelsRule.altitudes == frozenset({ScopeKind.CALLABLE})
    assert rc.severity is Severity.WARNING


def test_registered():
    assert any(isinstance(r, SentinelsRule) for r in RULE_REGISTRY)


def test_fires_on_sentinel_param(tmp_path: Path):
    cs = _callables(tmp_path)
    findings = list(SentinelsRule().check(cs["open_file"], SentinelsRule.default_config()))
    assert len(findings) == 1
    f = findings[0]
    assert f.disposition is Disposition.VERDICT
    assert f.action is Action.REPLACE_SENTINEL_TYPE
    assert f.severity is Severity.WARNING
    assert f.metadata["parameter"] == "mode"
    assert "mode" in f.message


def test_silent_on_non_sentinel(tmp_path: Path):
    cs = _callables(tmp_path)
    assert list(SentinelsRule().check(cs["plain"], SentinelsRule.default_config())) == []
