"""Tests for structural.any_type_density rule."""

from __future__ import annotations

from pathlib import Path

from slop._structural.any_type_density import any_type_density_kernel
from slop.models import RuleConfig, SlopConfig
from slop.rules.any_type_density import run_any_type_density

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _rc(**overrides) -> RuleConfig:
    params = {"threshold": 0.30, "min_annotations": 2}
    params.update(overrides)
    return RuleConfig(enabled=True, severity="warning", params=params)


def _sc(tmp_path: Path) -> SlopConfig:
    return SlopConfig(root=str(tmp_path))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

# Heavy Any usage — should fail at 30% threshold
_ANY_HEAVY = """\
from typing import Any, List, Dict

def process(data: Any) -> Any:
    result: Any = {}
    items: List[Any] = list(data)
    return result

def transform(x: int) -> int:
    return x * 2
"""

# No Any usage
_ANY_CLEAN = """\
from typing import List, Dict

def process(data: List[int]) -> Dict[str, int]:
    result: Dict[str, int] = {}
    for item in data:
        result[str(item)] = item
    return result
"""


# ---------------------------------------------------------------------------
# Kernel tests
# ---------------------------------------------------------------------------


def test_kernel_detects_any_usage(tmp_path: Path):
    (tmp_path / "a.py").write_text(_ANY_HEAVY)
    result = any_type_density_kernel(tmp_path, languages=["python"])
    assert result.files_searched >= 1
    entry = next((e for e in result.entries if e.file.endswith("a.py")), None)
    assert entry is not None
    assert entry.escape_count >= 3  # data: Any, -> Any, result: Any


def test_kernel_clean_file_has_zero_density(tmp_path: Path):
    (tmp_path / "a.py").write_text(_ANY_CLEAN)
    result = any_type_density_kernel(tmp_path, languages=["python"])
    for entry in result.entries:
        if entry.file.endswith("a.py"):
            assert entry.escape_count == 0


def test_kernel_density_is_fraction(tmp_path: Path):
    (tmp_path / "a.py").write_text(_ANY_HEAVY)
    result = any_type_density_kernel(tmp_path, languages=["python"])
    entry = next((e for e in result.entries if e.file.endswith("a.py")), None)
    if entry:
        assert 0.0 <= entry.density <= 1.0
        assert entry.density == round(entry.escape_count / entry.total_count, 4)


def test_kernel_entries_sorted_by_density_desc(tmp_path: Path):
    (tmp_path / "a.py").write_text(_ANY_HEAVY)
    (tmp_path / "b.py").write_text(_ANY_CLEAN)
    result = any_type_density_kernel(tmp_path, languages=["python"])
    densities = [e.density for e in result.entries]
    assert densities == sorted(densities, reverse=True)


def test_kernel_language_filter(tmp_path: Path):
    """Restricting to 'go' should not pick up Python files."""
    (tmp_path / "a.py").write_text(_ANY_HEAVY)
    result = any_type_density_kernel(tmp_path, languages=["go"])
    py_entries = [e for e in result.entries if e.file.endswith(".py")]
    assert py_entries == []


# ---------------------------------------------------------------------------
# Rule wrapper tests
# ---------------------------------------------------------------------------


def test_rule_pass_clean_file(tmp_path: Path):
    (tmp_path / "a.py").write_text(_ANY_CLEAN)
    result = run_any_type_density(tmp_path, _rc(threshold=0.30), _sc(tmp_path))
    assert result.status == "pass"
    assert result.violations == []


def test_rule_fail_heavy_any(tmp_path: Path):
    (tmp_path / "a.py").write_text(_ANY_HEAVY)
    result = run_any_type_density(
        tmp_path, _rc(threshold=0.10, min_annotations=2), _sc(tmp_path)
    )
    assert result.status == "fail"
    assert len(result.violations) >= 1
    v = result.violations[0]
    assert v.rule == "structural.types.escape_hatches"
    assert v.severity == "warning"
    assert v.value > 0.10


def test_rule_min_annotations_skips_small_files(tmp_path: Path):
    """Files with fewer annotations than min_annotations should be skipped."""
    (tmp_path / "a.py").write_text("def f(x: Any): return x\n")
    result = run_any_type_density(
        tmp_path, _rc(threshold=0.0, min_annotations=20), _sc(tmp_path)
    )
    assert result.status == "pass"


def test_rule_violation_metadata_keys(tmp_path: Path):
    (tmp_path / "a.py").write_text(_ANY_HEAVY)
    result = run_any_type_density(
        tmp_path, _rc(threshold=0.0, min_annotations=1), _sc(tmp_path)
    )
    if result.violations:
        v = result.violations[0]
        for key in ("language", "escape_count", "total_count", "density"):
            assert key in v.metadata, f"missing key: {key}"


def test_rule_summary_keys(tmp_path: Path):
    (tmp_path / "a.py").write_text(_ANY_CLEAN)
    result = run_any_type_density(tmp_path, _rc(), _sc(tmp_path))
    for key in ("files_scanned", "violations", "threshold"):
        assert key in result.summary, f"missing key: {key}"
