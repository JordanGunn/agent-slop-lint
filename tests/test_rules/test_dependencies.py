"""Tests for slop deps rule."""

from __future__ import annotations

from pathlib import Path

from slop.models import RuleConfig, SlopConfig
from slop.rules.dependencies import run_cycles


def test_deps_clean_when_no_cycles(tmp_path: Path):
    (tmp_path / "a.py").write_text("import os\n")
    (tmp_path / "b.py").write_text("import sys\n")
    rc = RuleConfig(enabled=True, severity="error", params={"fail_on_cycles": True})
    result = run_cycles(tmp_path, rc, SlopConfig(root=str(tmp_path)))
    assert result.status == "pass"
    assert result.violations == []


def test_deps_violation_when_cycle_exists(tmp_path: Path):
    # Create a circular import
    (tmp_path / "a.py").write_text("from b import something\n")
    (tmp_path / "b.py").write_text("from a import something\n")
    rc = RuleConfig(enabled=True, severity="error", params={"fail_on_cycles": True})
    result = run_cycles(tmp_path, rc, SlopConfig(root=str(tmp_path)))
    assert result.status == "fail"
    assert len(result.violations) >= 1
    assert "cycle" in result.violations[0].message
