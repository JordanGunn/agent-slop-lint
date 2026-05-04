"""Tests for lexical.tersity rule."""

from __future__ import annotations

from pathlib import Path

from slop.models import RuleConfig, SlopConfig
from slop.rules.tersity import run_tersity

def _rc(**overrides) -> RuleConfig:
    params = {
        "max_density": 0.50,
        "max_len": 2,
        "min_identifiers": 3,
    }
    params.update(overrides)
    return RuleConfig(enabled=True, severity="warning", params=params)

def _sc(tmp_path: Path) -> SlopConfig:
    return SlopConfig(root=str(tmp_path))

_RICH = """\
def compute_total_value(input_collection, scale_factor):
    accumulated_result = sum(input_collection) * scale_factor
    processed_output = accumulated_result + scale_factor
    return processed_output
"""

_TERSE = """\
def f(a, b, c, d, e, g):
    h = a + b
    m = c * d
    r = e + g + h + m
    return r
"""

_WITH_ALLOWED = """\
def iterate_matrix(matrix, rows, cols):
    result_list = []
    for i in range(rows):
        for j in range(cols):
            result_list.append(matrix[i][j])
    return result_list
"""

def test_rule_pass_rich_names(tmp_path: Path):
    (tmp_path / "a.py").write_text(_RICH)
    result = run_tersity(tmp_path, _rc(), _sc(tmp_path))
    assert result.status == "pass"

def test_rule_fail_terse_names(tmp_path: Path):
    (tmp_path / "a.py").write_text(_TERSE)
    result = run_tersity(tmp_path, _rc(max_density=0.50), _sc(tmp_path))
    assert result.status == "fail"
    assert result.violations[0].rule == "lexical.tersity"

def test_rule_allow_list_excludes_conventional_names(tmp_path: Path):
    (tmp_path / "a.py").write_text(_WITH_ALLOWED)
    result = run_tersity(tmp_path, _rc(max_density=0.30), _sc(tmp_path))
    assert result.status == "pass"

def test_rule_custom_allow_list(tmp_path: Path):
    src = "def f(a, b, c): return a + b + c"
    (tmp_path / "a.py").write_text(src)
    result_fail = run_tersity(tmp_path, _rc(max_density=0.10, min_identifiers=1), _sc(tmp_path))
    assert result_fail.status == "fail"
    
    result_pass = run_tersity(tmp_path, _rc(max_density=0.10, min_identifiers=1, allow_list=["a", "b", "c"]), _sc(tmp_path))
    assert result_pass.status == "pass"

def test_rule_min_identifiers_skips_tiny_function(tmp_path: Path):
    (tmp_path / "a.py").write_text("def f(a): return a\n")
    result = run_tersity(tmp_path, _rc(min_identifiers=10), _sc(tmp_path))
    assert result.status == "pass"

def test_rule_violation_metadata_keys(tmp_path: Path):
    (tmp_path / "a.py").write_text(_TERSE)
    result = run_tersity(tmp_path, _rc(max_density=0.0), _sc(tmp_path))
    assert result.status == "fail"
    v = result.violations[0]
    for key in ("short_identifiers", "short_count", "total_identifiers", "density"):
        assert key in v.metadata, f"missing key: {key}"

def test_rule_max_len_param(tmp_path: Path):
    src = "def fn(foo, bar): return foo + bar"
    (tmp_path / "a.py").write_text(src)
    result = run_tersity(tmp_path, _rc(max_density=0.20, max_len=3, min_identifiers=2), _sc(tmp_path))
    assert result.status == "fail"
