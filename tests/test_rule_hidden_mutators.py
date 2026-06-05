"""structure.hidden-mutators — in-place parameter mutation, REVIEW@WARNING verdict."""
from __future__ import annotations

from pathlib import Path

from slop.config import RuleConfig
from slop.finding import Action, Disposition, Severity
from slop.rules import RULE_REGISTRY
from slop.rules.hidden_mutators import HiddenMutatorsRule
from slop.scope import scan_corpus
from slop.scope.identity import ScopeKind

SRC = '''\
def accumulate(items: list):
    items.append(1)
    items.append(2)

def pure(count: int):
    return count + 1
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
    rc = HiddenMutatorsRule.default_config()
    assert HiddenMutatorsRule.altitudes == frozenset({ScopeKind.CALLABLE})
    assert rc.param("min_mutations") == 1


def test_registered():
    assert any(isinstance(r, HiddenMutatorsRule) for r in RULE_REGISTRY)


def test_fires_on_mutation(tmp_path: Path):
    cs = _callables(tmp_path)
    findings = list(HiddenMutatorsRule().check(cs["accumulate"], HiddenMutatorsRule.default_config()))
    assert len(findings) == 1
    f = findings[0]
    assert f.disposition is Disposition.VERDICT
    assert f.action is Action.REVIEW              # remedy is intent-dependent
    assert f.severity is Severity.WARNING          # REVIEW caps at WARNING
    assert f.value == 2                             # two .append() mutations
    assert "items" in f.message


def test_silent_on_pure(tmp_path: Path):
    cs = _callables(tmp_path)
    assert list(HiddenMutatorsRule().check(cs["pure"], HiddenMutatorsRule.default_config())) == []


def test_min_mutations_gate(tmp_path: Path):
    cs = _callables(tmp_path)
    cfg = RuleConfig(name=HiddenMutatorsRule.name, params={"min_mutations": 3})
    # accumulate has only 2 mutations — below the raised floor.
    assert list(HiddenMutatorsRule().check(cs["accumulate"], cfg)) == []
