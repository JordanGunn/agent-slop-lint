"""Tests for structural.god_module rule."""

from __future__ import annotations

from pathlib import Path

from slop._structural.god_module import god_module_kernel
from slop.models import RuleConfig, SlopConfig
from slop.rules.god_module import run_god_module


def _rc(threshold: int = 20) -> RuleConfig:
    return RuleConfig(enabled=True, severity="warning", params={"threshold": threshold})


def _sc(tmp_path: Path) -> SlopConfig:
    return SlopConfig(root=str(tmp_path))


def _funcs(n: int) -> str:
    """Generate a Python source with n top-level function definitions."""
    return "\n".join(f"def func_{i}():\n    pass\n" for i in range(n))


# ---------------------------------------------------------------------------
# Kernel
# ---------------------------------------------------------------------------


def test_kernel_counts_top_level_functions(tmp_path: Path):
    (tmp_path / "a.py").write_text(_funcs(5))
    result = god_module_kernel(tmp_path)
    entry = next(e for e in result.entries if e.file.endswith("a.py"))
    assert entry.definition_count == 5


def test_kernel_counts_classes(tmp_path: Path):
    src = "\n".join(f"class MyClass{i}:\n    pass\n" for i in range(3))
    (tmp_path / "a.py").write_text(src)
    result = god_module_kernel(tmp_path)
    entry = next(e for e in result.entries if e.file.endswith("a.py"))
    assert entry.definition_count == 3


def test_kernel_does_not_count_nested_functions(tmp_path: Path):
    src = (
        "def outer():\n"
        "    def inner1(): pass\n"
        "    def inner2(): pass\n"
        "    return inner1, inner2\n"
    )
    (tmp_path / "a.py").write_text(src)
    result = god_module_kernel(tmp_path)
    entry = next(e for e in result.entries if e.file.endswith("a.py"))
    # Only `outer` is top-level; inner1 and inner2 are nested
    assert entry.definition_count == 1


def test_kernel_mixes_funcs_and_classes(tmp_path: Path):
    src = "def f1(): pass\ndef f2(): pass\nclass C1: pass\nclass C2: pass\n"
    (tmp_path / "a.py").write_text(src)
    result = god_module_kernel(tmp_path)
    entry = next(e for e in result.entries if e.file.endswith("a.py"))
    assert entry.definition_count == 4


def test_kernel_records_loc(tmp_path: Path):
    src = _funcs(2)
    (tmp_path / "a.py").write_text(src)
    result = god_module_kernel(tmp_path)
    entry = next(e for e in result.entries if e.file.endswith("a.py"))
    assert entry.loc == len(src.splitlines())


def test_kernel_empty_file(tmp_path: Path):
    (tmp_path / "a.py").write_text("")
    result = god_module_kernel(tmp_path)
    entry = next(e for e in result.entries if e.file.endswith("a.py"))
    assert entry.definition_count == 0


def test_kernel_multiple_files_sorted_descending(tmp_path: Path):
    (tmp_path / "big.py").write_text(_funcs(10))
    (tmp_path / "small.py").write_text(_funcs(2))
    result = god_module_kernel(tmp_path)
    counts = [e.definition_count for e in result.entries]
    assert counts == sorted(counts, reverse=True)


def test_kernel_ignores_non_python_files(tmp_path: Path):
    (tmp_path / "data.txt").write_text("def not_a_function(): pass\n")
    result = god_module_kernel(tmp_path)
    # The .txt file has no recognised language, so it should not appear
    assert all(not e.file.endswith(".txt") for e in result.entries)


# ---------------------------------------------------------------------------
# Rule wrapper
# ---------------------------------------------------------------------------


def test_rule_pass_below_threshold(tmp_path: Path):
    (tmp_path / "a.py").write_text(_funcs(5))
    result = run_god_module(tmp_path, _rc(threshold=10), _sc(tmp_path))
    assert result.status == "pass"
    assert result.violations == []


def test_rule_fail_above_threshold(tmp_path: Path):
    (tmp_path / "a.py").write_text(_funcs(25))
    result = run_god_module(tmp_path, _rc(threshold=20), _sc(tmp_path))
    assert result.status == "fail"
    assert len(result.violations) == 1
    v = result.violations[0]
    assert v.rule == "structural.god_module"
    assert v.severity == "warning"
    assert v.value == 25
    assert v.threshold == 20


def test_rule_exactly_at_threshold_passes(tmp_path: Path):
    # threshold=N means flag if count > N (strictly greater than)
    (tmp_path / "a.py").write_text(_funcs(20))
    result = run_god_module(tmp_path, _rc(threshold=20), _sc(tmp_path))
    assert result.status == "pass"


def test_rule_summary_counts(tmp_path: Path):
    (tmp_path / "big.py").write_text(_funcs(25))
    (tmp_path / "small.py").write_text(_funcs(5))
    result = run_god_module(tmp_path, _rc(threshold=20), _sc(tmp_path))
    assert result.summary["violation_count"] == 1
    assert result.summary["files_checked"] >= 2
