"""structure.god-module rule — top-level definition count gating. Module altitude."""
from __future__ import annotations

from pathlib import Path

from slop.config import RuleConfig
from slop.finding import Action, Disposition, Severity
from slop.rules import RULE_REGISTRY
from slop.rules.god_module import GodModuleRule
from slop.scope import scan_corpus
from slop.scope.identity import ScopeKind

# 3 top-level defs (2 functions + 1 class). The method inside C must NOT count.
SRC = '''\
def f():
    return 1

def g():
    return 2

class C:
    def method(self):
        return 3
'''


def _module(tmp_path: Path):
    (tmp_path / "m.py").write_text(SRC)
    return scan_corpus(tmp_path, config=None).realms()[0].packages()[0].modules()[0]


def test_default_config_is_threshold_20_module():
    rc = GodModuleRule.default_config()
    assert rc.thresholds == {ScopeKind.MODULE.value: 20}
    assert rc.severity is Severity.WARNING
    assert GodModuleRule.altitudes == frozenset({ScopeKind.MODULE})


def test_registered():
    assert any(isinstance(r, GodModuleRule) for r in RULE_REGISTRY)


def test_fires_above_threshold(tmp_path: Path):
    mod = _module(tmp_path)
    rc = RuleConfig(name=GodModuleRule.name, severity=Severity.WARNING,
                    thresholds={ScopeKind.MODULE.value: 2})
    findings = list(GodModuleRule().check(mod, rc))
    assert len(findings) == 1
    f = findings[0]
    assert f.disposition is Disposition.VERDICT
    assert f.action is Action.SPLIT_MODULE
    assert f.value == 3 and f.threshold == 2  # 2 functions + 1 class; method excluded


def test_silent_at_or_below_threshold(tmp_path: Path):
    mod = _module(tmp_path)
    # 3 defs is far under the default 20.
    assert list(GodModuleRule().check(mod, GodModuleRule.default_config())) == []
