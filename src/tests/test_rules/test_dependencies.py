"""Tests for slop deps rule."""

from __future__ import annotations

from pathlib import Path

from slop._structural.deps import deps_kernel
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


def test_deps_kernel_tracks_external_imports_without_local_edges(tmp_path: Path):
    (tmp_path / "a.py").write_text("import os\nimport sys\n")
    result = deps_kernel(tmp_path)
    only = next(fd for fd in result.files if fd.file.endswith("a.py"))
    assert only.imports == ["os", "sys"]
    assert only.efferent == 0
    assert only.afferent == 0
    assert only.instability is None


def test_deps_kernel_deduplicates_imports_preserving_order(tmp_path: Path):
    (tmp_path / "a.py").write_text("import b\nfrom b import value\nimport c\nimport b\n")
    (tmp_path / "b.py").write_text("VALUE = 1\n")
    (tmp_path / "c.py").write_text("VALUE = 2\n")
    result = deps_kernel(tmp_path)
    only = next(fd for fd in result.files if fd.file.endswith("a.py"))
    assert only.imports == ["b", "c"]
    assert only.efferent == 2
    assert only.instability == 1.0


def test_deps_kernel_target_mode_filters_files_and_cycles(tmp_path: Path):
    (tmp_path / "a.py").write_text("import b\n")
    (tmp_path / "b.py").write_text("import a\n")
    (tmp_path / "c.py").write_text("import os\n")
    result = deps_kernel(tmp_path, target="a.py")
    assert [Path(fd.file).name for fd in result.files] == ["a.py"]
    assert len(result.cycles) == 1
    assert {Path(p).name for p in result.cycles[0]} == {"a.py", "b.py"}


def test_deps_kernel_max_results_sets_truncated(tmp_path: Path):
    (tmp_path / "a.py").write_text("import b\n")
    (tmp_path / "b.py").write_text("VALUE = 1\n")
    (tmp_path / "c.py").write_text("VALUE = 2\n")
    result = deps_kernel(tmp_path, max_results=1)
    assert len(result.files) == 1
    assert result.truncated is True


def test_deps_kernel_go_text_fallback_extracts_single_and_block_imports(tmp_path: Path):
    (tmp_path / "main.go").write_text(
        'package main\n\nimport "fmt"\n\nimport (\n    "os"\n    alias "path/filepath"\n)\n'
    )
    result = deps_kernel(tmp_path)
    only = next(fd for fd in result.files if fd.file.endswith("main.go"))
    assert only.imports == ["fmt", "os", "path/filepath"]


def test_deps_kernel_reports_strongly_connected_cycle_component(tmp_path: Path):
    (tmp_path / "a.py").write_text("import b\n")
    (tmp_path / "b.py").write_text("import c\n")
    (tmp_path / "c.py").write_text("import a\n")
    result = deps_kernel(tmp_path)
    assert len(result.cycles) == 1
    assert {Path(p).name for p in result.cycles[0]} == {"a.py", "b.py", "c.py"}


def test_deps_kernel_prefers_dotted_module_path_over_same_stem(tmp_path: Path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "main.py").write_text("import pkg.service\n")
    (tmp_path / "service.py").write_text("VALUE = 'root'\n")
    (tmp_path / "pkg" / "service.py").write_text("VALUE = 'pkg'\n")

    result = deps_kernel(tmp_path)
    root_service = next(
        fd for fd in result.files
        if Path(fd.file).name == "service.py" and Path(fd.file).parent == tmp_path
    )
    pkg_service = next(fd for fd in result.files if fd.file.endswith("/pkg/service.py"))

    assert root_service.afferent == 0
    assert pkg_service.afferent == 1
    assert Path(pkg_service.imported_by[0]).name == "main.py"
