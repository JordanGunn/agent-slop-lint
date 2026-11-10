"""structure.god-module: top-level definition count against the module limit."""
from __future__ import annotations

from pathlib import Path

from slop.config import RuleConfig
from slop.rules import RULE_REGISTRY
from slop.rules.god_module import GodModuleRule
from slop.scope import scan_corpus
from slop.scope.identity import ScopeKind

# 3 top-level defs (2 functions + 1 class). The method inside C must NOT count.
SRC = '''\
"""doc"""

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


def _cfg(limit) -> RuleConfig:
    return RuleConfig(name=GodModuleRule.name, thresholds={ScopeKind.MODULE.value: limit})


def test_default_config_is_threshold_20_module():
    rc = GodModuleRule.default_config()
    assert rc.thresholds == {ScopeKind.MODULE.value: 20}
    assert GodModuleRule.altitudes == frozenset({ScopeKind.MODULE})


def test_registered():
    assert any(isinstance(r, GodModuleRule) for r in RULE_REGISTRY)


def test_violation_fields_and_location(tmp_path: Path):
    mod = _module(tmp_path)
    [v] = list(GodModuleRule().check(mod, _cfg(2)))
    assert v.rule == "structure.god-module"
    assert v.path == str(tmp_path / "m.py")
    assert (v.line, v.column) == (1, 1)
    assert v.value == 3 and v.threshold == 2  # 2 functions + 1 class; method excluded
    assert "m" in v.message and "3" in v.message and "2" in v.message


def test_strictly_greater_than_limit(tmp_path: Path):
    mod = _module(tmp_path)
    assert list(GodModuleRule().check(mod, _cfg(3))) == []
    assert len(list(GodModuleRule().check(mod, _cfg(2)))) == 1


def test_default_limit_is_silent(tmp_path: Path):
    mod = _module(tmp_path)
    assert list(GodModuleRule().check(mod, GodModuleRule.default_config())) == []


def test_no_threshold_configured_is_silent(tmp_path: Path):
    mod = _module(tmp_path)
    assert list(GodModuleRule().check(mod, RuleConfig(name=GodModuleRule.name))) == []
