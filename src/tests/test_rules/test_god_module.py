"""Tests for ``god_module`` rule (rule-layer wrapper).

Substrate-native unit tests live in tests/test_v2/test_rule_god_module.py;
this file covers the rule's threshold / severity / summary plumbing.
"""
from __future__ import annotations

from pathlib import Path

from slop.linter.rule import Rule
from slop.config import Config
from slop.linter.rules.god_module import run_god_module
from slop.tree.tree import Tree


def _structure(root: Path):
    t = Tree(root)
    t.scan()
    return t.structure


def _rc(threshold: int = 20) -> Rule:
    return Rule(enabled=True, severity="warning", params={"thresholds": {"module": threshold}})


def _sc(tmp_path: Path) -> Config:
    return Config(root=str(tmp_path))


def _funcs(n: int) -> str:
    return "\n".join(f"def func_{i}():\n    pass\n" for i in range(n))


def test_rule_pass_below_threshold(tmp_path: Path):
    (tmp_path / "a.py").write_text(_funcs(5))
    result = run_god_module(_structure(tmp_path), _rc(threshold=10), _sc(tmp_path))
    assert result.status == "pass"
    assert result.violations == []


def test_rule_fail_above_threshold(tmp_path: Path):
    (tmp_path / "a.py").write_text(_funcs(25))
    result = run_god_module(_structure(tmp_path), _rc(threshold=20), _sc(tmp_path))
    assert result.status == "fail"
    assert len(result.violations) == 1
    v = result.violations[0]
    assert v.rule == "god_module"
    assert v.severity == "warning"
    assert v.value == 25
    assert v.threshold == 20


def test_rule_exactly_at_threshold_passes(tmp_path: Path):
    # threshold=N means flag if count > N (strictly greater than).
    (tmp_path / "a.py").write_text(_funcs(20))
    result = run_god_module(_structure(tmp_path), _rc(threshold=20), _sc(tmp_path))
    assert result.status == "pass"


def test_rule_summary_counts(tmp_path: Path):
    (tmp_path / "big.py").write_text(_funcs(25))
    (tmp_path / "small.py").write_text(_funcs(5))
    result = run_god_module(_structure(tmp_path), _rc(threshold=20), _sc(tmp_path))
    assert result.summary["violation_count"] == 1
    assert result.summary["files_checked"] >= 2
