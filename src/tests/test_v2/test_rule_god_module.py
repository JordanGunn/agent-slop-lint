"""Tests for the v2 ``god_module`` rule.

Exercises ``run_god_module`` end-to-end via the Structure view.
Verifies the rule emits per-file violations when top-level definition
counts exceed the threshold, and that methods nested inside a class
do NOT contribute to the count (god-module measures module breadth;
the god-class concern is separately captured by WMC).
"""
from __future__ import annotations

from pathlib import Path

from slop.linter.rule_config import RuleConfig
from slop.config import Config
from slop.structure.metrics.god_module import run_god_module
from slop.tree.tree import Tree


def _rc(threshold: int = 20) -> RuleConfig:
    return RuleConfig(enabled=True, severity="warning", params={"thresholds": {"module": threshold}})


def _sc(tmp_path: Path) -> Config:
    return Config(root=str(tmp_path))


def _structure(tmp_path: Path):
    cb = Tree(tmp_path)
    cb.scan()
    return cb.structure


def _pyfuncs(n: int) -> str:
    return "\n".join(f"def f{i}(): pass" for i in range(n))


def _pyclasses(n: int) -> str:
    return "\n".join(f"class C{i}: pass" for i in range(n))


class TestGodModuleV2:
    def test_below_threshold_passes(self, tmp_path: Path):
        (tmp_path / "a.py").write_text(_pyfuncs(10))
        result = run_god_module(_structure(tmp_path), _rc(20), _sc(tmp_path))
        assert result.status == "pass"
        assert result.violations == []

    def test_above_threshold_flags(self, tmp_path: Path):
        (tmp_path / "a.py").write_text(_pyfuncs(25))
        result = run_god_module(_structure(tmp_path), _rc(20), _sc(tmp_path))
        assert result.status == "fail"
        assert len(result.violations) == 1
        assert result.violations[0].value == 25
        assert result.violations[0].file == "a.py"

    def test_class_methods_dont_count(self, tmp_path: Path):
        # 1 top-level class + 25 methods inside it = 1 top-level definition.
        # Class methods are a god-class signal (WMC), not god-module.
        methods = "\n".join(f"    def m{i}(self): pass" for i in range(25))
        (tmp_path / "a.py").write_text("class Big:\n" + methods + "\n")
        result = run_god_module(_structure(tmp_path), _rc(20), _sc(tmp_path))
        assert result.status == "pass"

    def test_top_level_classes_count(self, tmp_path: Path):
        (tmp_path / "a.py").write_text(_pyclasses(22))
        result = run_god_module(_structure(tmp_path), _rc(20), _sc(tmp_path))
        assert result.status == "fail"
        assert result.violations[0].value == 22

    def test_mixed_funcs_and_classes(self, tmp_path: Path):
        (tmp_path / "a.py").write_text(_pyfuncs(10) + "\n" + _pyclasses(12))
        result = run_god_module(_structure(tmp_path), _rc(20), _sc(tmp_path))
        assert result.status == "fail"
        assert result.violations[0].value == 22

    def test_java_class_with_many_methods_not_god_module(self, tmp_path: Path):
        # Java: 25 methods nested inside a single class. The class itself
        # is the only top-level definition → not a god module.
        methods = "\n".join(f"  void m{i}() {{}}" for i in range(25))
        (tmp_path / "A.java").write_text("class A {\n" + methods + "\n}\n")
        result = run_god_module(_structure(tmp_path), _rc(20), _sc(tmp_path))
        assert result.status == "pass"

    def test_go_many_functions_flagged(self, tmp_path: Path):
        # Go: 23 top-level functions → above default threshold of 20.
        (tmp_path / "p.go").write_text(
            "package p\n" + "\n".join(f"func F{i}() {{}}" for i in range(23))
        )
        result = run_god_module(_structure(tmp_path), _rc(20), _sc(tmp_path))
        assert result.status == "fail"
        assert result.violations[0].value == 23

    def test_lambdas_dont_count(self, tmp_path: Path):
        # 5 module-level lambda assignments would be 5 LAMBDA callables.
        # god-module measures "definitions", not anonymous values.
        src = "\n".join(f"f{i} = lambda x: x" for i in range(25))
        (tmp_path / "a.py").write_text(src)
        result = run_god_module(_structure(tmp_path), _rc(20), _sc(tmp_path))
        # The named assignments aren't function definitions; lambdas are
        # excluded. Count should be 0 (no top-level def or class).
        assert result.status == "pass"

    def test_multiple_files_emit_per_file_violations(self, tmp_path: Path):
        (tmp_path / "big1.py").write_text(_pyfuncs(25))
        (tmp_path / "big2.py").write_text(_pyfuncs(30))
        (tmp_path / "small.py").write_text(_pyfuncs(5))
        result = run_god_module(_structure(tmp_path), _rc(20), _sc(tmp_path))
        assert result.status == "fail"
        assert len(result.violations) == 2
        # Sorted by count desc: big2 (30) before big1 (25).
        assert result.violations[0].value == 30
        assert result.violations[0].file == "big2.py"
        assert result.violations[1].value == 25
        assert result.violations[1].file == "big1.py"

    def test_summary_files_checked(self, tmp_path: Path):
        (tmp_path / "a.py").write_text(_pyfuncs(3))
        (tmp_path / "b.py").write_text(_pyfuncs(3))
        result = run_god_module(_structure(tmp_path), _rc(20), _sc(tmp_path))
        assert result.summary["files_checked"] == 2
        assert result.summary["violation_count"] == 0
