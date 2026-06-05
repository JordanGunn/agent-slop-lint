"""complexity.cognitive rule — threshold gating + emission, and the deliberate
Callable-only altitude (no class gate, mirroring complexity.cyclomatic).

Metric values are oracle-pinned in test_complexity (m.h cognitive == 7,
m.branchy == 2); this asserts the *rule* turns them into the right verdict.
"""
from __future__ import annotations

from pathlib import Path

from slop.config import RuleConfig
from slop.finding import Action, Disposition, Severity
from slop.rules import RULE_REGISTRY
from slop.rules.cognitive import CognitiveRule
from slop.scope import scan_corpus
from slop.scope.identity import ScopeKind

SRC = '''\
def h(x, y):
    if x:
        if y and x > 0:
            return 1
    for i in range(x):
        while i:
            pass
    return 0

def branchy(a):
    if a > 0:
        return 1
    elif a < 0:
        return 2
    else:
        return 3
'''


def _callables(tmp_path: Path) -> dict:
    (tmp_path / "m.py").write_text(SRC)
    corpus = scan_corpus(tmp_path, config=None)
    return {c.qualname: c for c in corpus._iter_callables()}


def test_default_config_is_campbell_15_callable_only():
    rc = CognitiveRule.default_config()
    assert rc.thresholds == {ScopeKind.CALLABLE.value: 15}
    assert rc.severity is Severity.ERROR
    assert CognitiveRule.altitudes == frozenset({ScopeKind.CALLABLE})


def test_registered():
    assert any(isinstance(r, CognitiveRule) for r in RULE_REGISTRY)


def test_fires_above_threshold(tmp_path: Path):
    cs = _callables(tmp_path)
    rc = RuleConfig(name=CognitiveRule.name, severity=Severity.ERROR,
                    thresholds={ScopeKind.CALLABLE.value: 5})
    findings = list(CognitiveRule().check(cs["m.h"], rc))
    assert len(findings) == 1
    f = findings[0]
    assert f.disposition is Disposition.VERDICT
    assert f.action is Action.REDUCE_COMPLEXITY
    assert f.value == 7 and f.threshold == 5
    assert f.severity is Severity.ERROR


def test_silent_at_or_below_threshold(tmp_path: Path):
    cs = _callables(tmp_path)
    rc = RuleConfig(name=CognitiveRule.name,
                    thresholds={ScopeKind.CALLABLE.value: 5})
    # branchy cognitive == 2 (< 5); h == 7 but the default 15 also clears it.
    assert list(CognitiveRule().check(cs["m.branchy"], rc)) == []
    default_rc = CognitiveRule.default_config()
    assert list(CognitiveRule().check(cs["m.h"], default_rc)) == []
