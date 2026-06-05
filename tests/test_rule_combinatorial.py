"""complexity.combinatorial rule — threshold gating + emission, and the
deliberate Callable-only altitude (no class gate, the complexity-family decision).

Metric values are oracle-pinned in test_complexity (m.h NPath == 9,
m.branchy == 3); this asserts the *rule* turns them into the right verdict.
"""
from __future__ import annotations

from pathlib import Path

from slop.config import RuleConfig
from slop.finding import Action, Disposition, Severity
from slop.rules import RULE_REGISTRY
from slop.rules.combinatorial import CombinatorialRule
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


def test_default_config_is_nejmeh_400_callable_only():
    rc = CombinatorialRule.default_config()
    assert rc.thresholds == {ScopeKind.CALLABLE.value: 400}
    assert rc.severity is Severity.ERROR
    assert CombinatorialRule.altitudes == frozenset({ScopeKind.CALLABLE})


def test_registered():
    assert any(isinstance(r, CombinatorialRule) for r in RULE_REGISTRY)


def test_fires_above_threshold(tmp_path: Path):
    cs = _callables(tmp_path)
    rc = RuleConfig(name=CombinatorialRule.name, severity=Severity.ERROR,
                    thresholds={ScopeKind.CALLABLE.value: 5})
    findings = list(CombinatorialRule().check(cs["m.h"], rc))
    assert len(findings) == 1
    f = findings[0]
    assert f.disposition is Disposition.VERDICT
    assert f.action is Action.REDUCE_COMPLEXITY
    assert f.value == 9 and f.threshold == 5
    assert f.severity is Severity.ERROR


def test_silent_at_or_below_threshold(tmp_path: Path):
    cs = _callables(tmp_path)
    rc = RuleConfig(name=CombinatorialRule.name,
                    thresholds={ScopeKind.CALLABLE.value: 5})
    # branchy NPath == 3 (< 5); h == 9 but the default 400 clears it too.
    assert list(CombinatorialRule().check(cs["m.branchy"], rc)) == []
    default_rc = CombinatorialRule.default_config()
    assert list(CombinatorialRule().check(cs["m.h"], default_rc)) == []
