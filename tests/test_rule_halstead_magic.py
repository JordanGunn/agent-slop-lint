"""halstead-volume and magic-literal: limit gating, location and wording."""
from __future__ import annotations

from pathlib import Path

from slop.config import RuleConfig
from slop.rules import RULE_REGISTRY
from slop.rules.halstead import HalsteadVolumeRule
from slop.rules.magic_literal import MagicLiteralRule
from slop.scope import scan_corpus
from slop.scope.identity import ScopeKind

SRC = '''\
def dense(a, b, c):
    x = a * b + c * a - b * c
    y = x * x + a * a + b * b + c * c
    z = (x + y) * (x - y) + (a + b) * (a - b)
    return x * y * z + a * b * c + z * z

def tidy(a):
    return a

def limits(x):
    return x > 15 or x < -40
'''


def _callables(tmp_path: Path) -> dict:
    (tmp_path / "m.py").write_text(SRC)
    return {c.qualname: c for c in scan_corpus(tmp_path, config=None)._iter_callables()}


def _check(rule, component, limit):
    return list(rule.check(component, RuleConfig(name=rule.name, options={"limit": limit})))


def test_defaults_and_registration():
    assert HalsteadVolumeRule.default_config().options == {"limit": 1000}
    assert MagicLiteralRule.default_config().options == {"limit": 0}
    assert HalsteadVolumeRule.altitudes == MagicLiteralRule.altitudes == frozenset({ScopeKind.CALLABLE})
    assert {"halstead-volume", "magic-literal"} <= {r.name for r in RULE_REGISTRY}


def test_halstead_volume_reports_only_a_callable_over_the_limit(tmp_path: Path):
    cs = _callables(tmp_path)
    [v] = _check(HalsteadVolumeRule(), cs["m.dense"], 100)
    assert (v.rule, v.line, v.threshold) == ("halstead-volume", 1, 100)
    assert v.value > 100 and "m.dense has Halstead volume" in v.message
    assert _check(HalsteadVolumeRule(), cs["m.dense"], v.value) == []     # strictly greater
    assert _check(HalsteadVolumeRule(), cs["m.tidy"], 100) == []


def test_magic_literal_counts_distinct_values_against_the_limit(tmp_path: Path):
    cs = _callables(tmp_path)
    [v] = _check(MagicLiteralRule(), cs["m.limits"], 0)
    assert (v.value, v.threshold) == (2, 0)
    assert "15, 40" in v.message
    assert _check(MagicLiteralRule(), cs["m.limits"], 2) == []
    assert _check(MagicLiteralRule(), cs["m.tidy"], 0) == []
