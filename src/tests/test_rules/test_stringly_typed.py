"""Tests for structural.stringly_typed rule."""

from __future__ import annotations

from pathlib import Path

from slop._structural.stringly_typed import stringly_typed_kernel
from slop.models import RuleConfig, SlopConfig
from slop.rules.stringly_typed import run_stringly_typed

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _rc(**overrides) -> RuleConfig:
    params = {"max_cardinality": 8, "require_str_annotation": True}
    params.update(overrides)
    return RuleConfig(enabled=True, severity="warning", params=params)


def _sc(tmp_path: Path) -> SlopConfig:
    return SlopConfig(root=str(tmp_path))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

# Function with a clear stringly-typed sentinel parameter
_STRINGLY = """\
def set_log_level(level: str) -> None:
    pass
"""

# Function with non-sentinel str parameter (name doesn't match sentinel list)
_NON_SENTINEL_STR = """\
def greet(message: str) -> str:
    return f"Hello, {message}"
"""

# Function with int-typed sentinel name (should NOT be flagged — wrong type)
_INT_SENTINEL = """\
def set_level(level: int) -> None:
    pass
"""

# Untyped sentinel parameter (only flagged when require_str_annotation=False)
_UNTYPED_SENTINEL = """\
def change_mode(mode) -> None:
    pass
"""

# Multiple sentinel parameters in one function
_MULTI_SENTINEL = """\
def configure(mode: str, status: str, level: str) -> None:
    pass
"""

# Sentinel name with trailing underscore (PEP 8 convention)
_TRAILING_UNDERSCORE = """\
def select_type(type_: str) -> None:
    pass
"""


# ---------------------------------------------------------------------------
# Kernel tests
# ---------------------------------------------------------------------------


def test_kernel_detects_sentinel_str_param(tmp_path: Path):
    (tmp_path / "a.py").write_text(_STRINGLY)
    result = stringly_typed_kernel(tmp_path)
    entry = next(
        (e for e in result.entries if e.function_name == "set_log_level"), None
    )
    assert entry is not None
    assert entry.param_name == "level"
    assert entry.annotated is True


def test_kernel_ignores_non_sentinel_str(tmp_path: Path):
    (tmp_path / "a.py").write_text(_NON_SENTINEL_STR)
    result = stringly_typed_kernel(tmp_path)
    assert all(e.function_name != "greet" for e in result.entries)


def test_kernel_ignores_int_typed_sentinel(tmp_path: Path):
    (tmp_path / "a.py").write_text(_INT_SENTINEL)
    result = stringly_typed_kernel(tmp_path)
    # int-typed sentinel should NOT be flagged
    assert all(e.function_name != "set_level" for e in result.entries)


def test_kernel_require_annotation_skips_untyped(tmp_path: Path):
    (tmp_path / "a.py").write_text(_UNTYPED_SENTINEL)
    result = stringly_typed_kernel(tmp_path, require_str_annotation=True)
    assert all(e.function_name != "change_mode" for e in result.entries)


def test_kernel_no_annotation_required_detects_untyped(tmp_path: Path):
    (tmp_path / "a.py").write_text(_UNTYPED_SENTINEL)
    result = stringly_typed_kernel(tmp_path, require_str_annotation=False)
    entry = next(
        (e for e in result.entries if e.function_name == "change_mode"), None
    )
    assert entry is not None
    assert entry.annotated is False


def test_kernel_multiple_sentinel_params(tmp_path: Path):
    (tmp_path / "a.py").write_text(_MULTI_SENTINEL)
    result = stringly_typed_kernel(tmp_path)
    fn_entries = [e for e in result.entries if e.function_name == "configure"]
    assert len(fn_entries) == 3  # mode, status, level


def test_kernel_trailing_underscore_param(tmp_path: Path):
    """type_ should be recognized as the 'type' sentinel."""
    (tmp_path / "a.py").write_text(_TRAILING_UNDERSCORE)
    result = stringly_typed_kernel(tmp_path)
    entry = next(
        (e for e in result.entries if e.function_name == "select_type"), None
    )
    assert entry is not None


# ---------------------------------------------------------------------------
# Rule wrapper tests
# ---------------------------------------------------------------------------


def test_rule_fail_sentinel_str(tmp_path: Path):
    (tmp_path / "a.py").write_text(_STRINGLY)
    result = run_stringly_typed(tmp_path, _rc(max_cardinality=0), _sc(tmp_path))
    assert result.status == "fail"
    assert len(result.violations) >= 1
    v = result.violations[0]
    assert v.rule == "structural.types.sentinels"
    assert "level" in v.message


def test_rule_pass_non_sentinel(tmp_path: Path):
    (tmp_path / "a.py").write_text(_NON_SENTINEL_STR)
    result = run_stringly_typed(tmp_path, _rc(), _sc(tmp_path))
    assert result.status == "pass"


def test_rule_violation_metadata_keys(tmp_path: Path):
    (tmp_path / "a.py").write_text(_STRINGLY)
    result = run_stringly_typed(tmp_path, _rc(max_cardinality=0), _sc(tmp_path))
    if result.violations:
        v = result.violations[0]
        for key in ("param_name", "annotated", "call_site_literals",
                    "call_site_count"):
            assert key in v.metadata, f"missing key: {key}"


def test_rule_summary_keys(tmp_path: Path):
    (tmp_path / "a.py").write_text(_NON_SENTINEL_STR)
    result = run_stringly_typed(tmp_path, _rc(), _sc(tmp_path))
    for key in ("functions_analyzed", "files_searched", "violations",
                "max_cardinality"):
        assert key in result.summary, f"missing key: {key}"
