"""Tests for ``structural.deps`` — cycle detection on the substrate-native dependency graph."""
from __future__ import annotations

from pathlib import Path

from slop.config.models import RuleConfig, SlopConfig
from slop.structure.rules.dependencies import run_cycles
from slop.tree.tree import Tree


def _structure(root: Path):
    t = Tree(root)
    t.scan()
    return t.structure


def _rc(*, fail_on_cycles: bool = True, severity: str = "error") -> RuleConfig:
    return RuleConfig(enabled=True, severity=severity, params={"fail_on_cycles": fail_on_cycles})


def test_deps_clean_when_no_cycles(tmp_path: Path):
    (tmp_path / "a.py").write_text("import os\n")
    (tmp_path / "b.py").write_text("import sys\n")
    result = run_cycles(_structure(tmp_path), _rc(), SlopConfig(root=str(tmp_path)))
    assert result.status == "pass"
    assert result.violations == []


def test_deps_violation_when_two_node_cycle_exists(tmp_path: Path):
    (tmp_path / "a.py").write_text("from b import something\n")
    (tmp_path / "b.py").write_text("from a import something\n")
    result = run_cycles(_structure(tmp_path), _rc(), SlopConfig(root=str(tmp_path)))
    assert result.status == "fail"
    assert len(result.violations) == 1
    assert "cycle" in result.violations[0].message


def test_deps_detects_strongly_connected_three_node_cycle(tmp_path: Path):
    (tmp_path / "a.py").write_text("import b\n")
    (tmp_path / "b.py").write_text("import c\n")
    (tmp_path / "c.py").write_text("import a\n")
    result = run_cycles(_structure(tmp_path), _rc(), SlopConfig(root=str(tmp_path)))
    assert result.status == "fail"
    assert len(result.violations) == 1
    cycle = result.violations[0].metadata["cycle"]
    assert {Path(p).name for p in cycle} == {"a.py", "b.py", "c.py"}


def test_deps_fail_on_cycles_false_suppresses_violation(tmp_path: Path):
    (tmp_path / "a.py").write_text("from b import x\n")
    (tmp_path / "b.py").write_text("from a import x\n")
    result = run_cycles(
        _structure(tmp_path),
        _rc(fail_on_cycles=False),
        SlopConfig(root=str(tmp_path)),
    )
    assert result.status == "pass"
    assert result.violations == []
    assert result.summary["cycles_found"] == 1


def test_deps_summary_reports_files_analyzed_and_cycles_found(tmp_path: Path):
    (tmp_path / "a.py").write_text("import b\n")
    (tmp_path / "b.py").write_text("import a\n")
    (tmp_path / "lonely.py").write_text("VALUE = 1\n")
    result = run_cycles(_structure(tmp_path), _rc(), SlopConfig(root=str(tmp_path)))
    assert result.summary["files_analyzed"] == 3
    assert result.summary["cycles_found"] == 1


def test_deps_dotted_module_path_preferred_over_same_stem(tmp_path: Path):
    """``import pkg.service`` resolves to pkg/service.py, not to the root service.py.

    Verifies the Intent A module index resolution: dotted forms take
    precedence over bare-stem fallbacks, so a cycle through pkg.service
    is correctly attributed.
    """
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("")
    (tmp_path / "main.py").write_text("import pkg.service\n")
    (tmp_path / "service.py").write_text("VALUE = 'root'\n")
    (tmp_path / "pkg" / "service.py").write_text("from main import VALUE\n")
    # main → pkg/service.py → main: a 2-node cycle. The root service.py
    # is uninvolved (no inbound edges).
    result = run_cycles(_structure(tmp_path), _rc(), SlopConfig(root=str(tmp_path)))
    assert result.status == "fail"
    cycle_files = {Path(p).name for p in result.violations[0].metadata["cycle"]}
    assert cycle_files == {"main.py", "service.py"}
    # The root service.py is one of two service.py-named files; verify
    # the cycle file is in pkg/ via parent-directory check.
    parents = {Path(p).parent.name for p in result.violations[0].metadata["cycle"]}
    assert "pkg" in parents
