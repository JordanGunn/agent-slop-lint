"""Tests for slop npath rule."""

from __future__ import annotations

from pathlib import Path

from slop.models import RuleConfig, SlopConfig
from slop.rules.npath import run_npath

_LINEAR = "def f(x):\n    y = x + 1\n    return y\n"  # NPath=1

# 10 sequential independent ifs → NPath = 2^10 = 1024.
_SEQUENTIAL_IFS = """\
def f(a, b, c, d, e, f, g, h, i, j):
    x = 0
    if a: x += 1
    if b: x += 1
    if c: x += 1
    if d: x += 1
    if e: x += 1
    if f: x += 1
    if g: x += 1
    if h: x += 1
    if i: x += 1
    if j: x += 1
    return x
"""


def _write_file(tmp_path: Path, source: str, name: str = "sample.py") -> Path:
    f = tmp_path / name
    f.write_text(source)
    return tmp_path


def _slop_config() -> SlopConfig:
    return SlopConfig(rules={})


def _rule_config(**overrides) -> RuleConfig:
    defaults = {"npath_threshold": 200}
    defaults.update(overrides)
    return RuleConfig(enabled=True, severity="error", params=defaults)


def test_npath_passes_on_linear_function(tmp_path: Path) -> None:
    root = _write_file(tmp_path, _LINEAR)
    result = run_npath(root, _rule_config(), _slop_config())
    assert result.status == "pass"
    assert result.violations == []
    assert result.summary["functions_checked"] >= 1


def test_npath_flags_sequential_ifs(tmp_path: Path) -> None:
    # 10 sequential ifs multiplies to 1024, which trips the default 200 threshold.
    root = _write_file(tmp_path, _SEQUENTIAL_IFS)
    result = run_npath(root, _rule_config(), _slop_config())
    assert result.status == "fail"
    assert any(v.symbol == "f" for v in result.violations)
    flagged = next(v for v in result.violations if v.symbol == "f")
    assert flagged.value is not None and flagged.value > 200
    assert flagged.rule == "npath"


def test_npath_respects_custom_threshold(tmp_path: Path) -> None:
    root = _write_file(tmp_path, _SEQUENTIAL_IFS)
    # Raise threshold above 1024 and the violation disappears.
    result = run_npath(root, _rule_config(npath_threshold=2000), _slop_config())
    assert result.status == "pass"
    assert result.violations == []


def test_npath_flags_at_low_threshold(tmp_path: Path) -> None:
    root = _write_file(tmp_path, _LINEAR)
    # Linear NPath is 1; threshold 0 should flag it.
    result = run_npath(root, _rule_config(npath_threshold=0), _slop_config())
    assert result.status == "fail"
    assert len(result.violations) >= 1
