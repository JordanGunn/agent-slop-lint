"""structure.escape-hatches rule — density gating, the min_annotations noise
floor, and the additive REPLACE_ESCAPE_TYPE action. Module altitude."""
from __future__ import annotations

from pathlib import Path

from slop.finding import Action, Disposition, Severity
from slop.rules import RULE_REGISTRY
from slop.rules.escape_hatches import EscapeHatchesRule
from slop.scope import scan_corpus
from slop.scope.identity import ScopeKind

# 6 annotations, 4 escape-hatch (a,b,return,d) => density 0.667 > 0.30, total >= 5.
FIRES = '''\
from typing import Any

def f(a: Any, b: Any, c: int) -> Any:
    d: Any = 1
    e: int = 2
    return d
'''

# 2 annotations (both Any => density 1.0) but total < 5 floor => must stay silent.
BELOW_FLOOR = '''\
from typing import Any

def g(x: Any) -> Any:
    return x
'''

# 6 annotations, 1 escape => density 0.167 < 0.30 => silent.
LOW_DENSITY = '''\
from typing import Any

def h(a: int, b: str, c: float, d: bool) -> int:
    e: Any = 1
    return a
'''


def _module(tmp_path: Path, src: str):
    (tmp_path / "m.py").write_text(src)
    corpus = scan_corpus(tmp_path, config=None)
    return corpus.realms()[0].packages()[0].modules()[0]


def test_default_config_is_module_altitude():
    rc = EscapeHatchesRule.default_config()
    assert rc.thresholds == {ScopeKind.MODULE.value: 0.30}
    assert rc.param("min_annotations") == 5
    assert rc.severity is Severity.WARNING
    assert EscapeHatchesRule.altitudes == frozenset({ScopeKind.MODULE})


def test_registered():
    assert any(isinstance(r, EscapeHatchesRule) for r in RULE_REGISTRY)


def test_fires_above_threshold(tmp_path: Path):
    mod = _module(tmp_path, FIRES)
    findings = list(EscapeHatchesRule().check(mod, EscapeHatchesRule.default_config()))
    assert len(findings) == 1
    f = findings[0]
    assert f.disposition is Disposition.VERDICT
    assert f.action is Action.REPLACE_ESCAPE_TYPE
    assert f.value == round(4 / 6, 4)
    assert f.threshold == 0.30
    assert f.severity is Severity.WARNING


def test_silent_below_annotation_floor(tmp_path: Path):
    mod = _module(tmp_path, BELOW_FLOOR)
    # density is 1.0 but only 2 annotations (< 5) — the noise floor must suppress it.
    assert list(EscapeHatchesRule().check(mod, EscapeHatchesRule.default_config())) == []


def test_silent_below_density_threshold(tmp_path: Path):
    mod = _module(tmp_path, LOW_DENSITY)
    assert list(EscapeHatchesRule().check(mod, EscapeHatchesRule.default_config())) == []
