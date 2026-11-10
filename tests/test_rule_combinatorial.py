"""complexity.combinatorial: threshold gating and violation location (values pinned in test_complexity)."""
from __future__ import annotations

from pathlib import Path

from slop.config import RuleConfig
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


def _cfg(limit) -> RuleConfig:
    return RuleConfig(name=CombinatorialRule.name, thresholds={ScopeKind.CALLABLE.value: limit})


def test_default_config_is_callable_400():
    rc = CombinatorialRule.default_config()
    assert rc.thresholds == {ScopeKind.CALLABLE.value: 400}
    assert CombinatorialRule.altitudes == frozenset({ScopeKind.CALLABLE})


def test_registered():
    assert any(isinstance(r, CombinatorialRule) for r in RULE_REGISTRY)


def test_violation_fields_and_location(tmp_path: Path):
    cs = _callables(tmp_path)
    [v] = list(CombinatorialRule().check(cs["m.h"], _cfg(5)))
    assert v.rule == "complexity.combinatorial"
    assert v.path == str(tmp_path / "m.py")
    assert (v.line, v.column) == (1, 1)
    assert v.value == 9 and v.threshold == 5
    assert "m.h" in v.message and "9" in v.message and "5" in v.message
    assert v.as_dict()["value"] == 9


def test_located_at_the_callable_not_the_file_start(tmp_path: Path):
    cs = _callables(tmp_path)
    [v] = list(CombinatorialRule().check(cs["m.branchy"], _cfg(2)))
    assert (v.line, v.column) == (10, 1)


def test_strictly_greater_than_limit(tmp_path: Path):
    cs = _callables(tmp_path)
    assert list(CombinatorialRule().check(cs["m.h"], _cfg(9))) == []
    assert len(list(CombinatorialRule().check(cs["m.h"], _cfg(8)))) == 1


def test_below_threshold_and_default_are_silent(tmp_path: Path):
    cs = _callables(tmp_path)
    assert list(CombinatorialRule().check(cs["m.branchy"], _cfg(5))) == []
    assert list(CombinatorialRule().check(cs["m.h"], CombinatorialRule.default_config())) == []


def test_no_threshold_configured_is_silent(tmp_path: Path):
    cs = _callables(tmp_path)
    assert list(CombinatorialRule().check(cs["m.h"], RuleConfig(name=CombinatorialRule.name))) == []
