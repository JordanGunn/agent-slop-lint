"""Integration tests for structural.complexity.combinatorial (NPath, view-native)."""

from __future__ import annotations

from pathlib import Path

from slop.linter.rule import Rule
from slop.config import Config
from slop.linter.rules.combinatorial import run_combinatorial
from slop.tree.tree import Tree

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


def _structure(tmp_path: Path, source: str, name: str = "sample.py"):
    (tmp_path / name).write_text(source)
    tree = Tree(tmp_path)
    tree.scan()
    return tree.structure


def _slop_config(tmp_path: Path) -> Config:
    return Config(root=str(tmp_path), rules={})


def _rule_config(**overrides) -> Rule:
    threshold = overrides.pop("threshold", 400)
    params: dict = {"thresholds": {"function": threshold}}
    params.update(overrides)
    return Rule(enabled=True, severity="error", params=params)


def test_combinatorial_passes_on_linear_function(tmp_path: Path) -> None:
    result = run_combinatorial(
        _structure(tmp_path, _LINEAR), _rule_config(), _slop_config(tmp_path),
    )
    assert result.status == "pass"
    assert result.violations == []
    assert result.summary["functions_checked"] >= 1


def test_combinatorial_flags_sequential_ifs(tmp_path: Path) -> None:
    # 10 sequential ifs multiplies to 1024, which trips the default 400 threshold.
    result = run_combinatorial(
        _structure(tmp_path, _SEQUENTIAL_IFS), _rule_config(), _slop_config(tmp_path),
    )
    assert result.status == "fail"
    assert any(v.symbol == "f" for v in result.violations)
    flagged = next(v for v in result.violations if v.symbol == "f")
    assert flagged.value is not None and flagged.value > 400
    assert flagged.rule == "complexity.combinatorial"


def test_combinatorial_respects_custom_threshold(tmp_path: Path) -> None:
    # Raise threshold above 1024 and the violation disappears.
    result = run_combinatorial(
        _structure(tmp_path, _SEQUENTIAL_IFS),
        _rule_config(threshold=2000),
        _slop_config(tmp_path),
    )
    assert result.status == "pass"
    assert result.violations == []


def test_combinatorial_flags_at_low_threshold(tmp_path: Path) -> None:
    # Linear NPath is 1; threshold 0 should flag it.
    result = run_combinatorial(
        _structure(tmp_path, _LINEAR),
        _rule_config(threshold=0),
        _slop_config(tmp_path),
    )
    assert result.status == "fail"
    assert len(result.violations) >= 1
