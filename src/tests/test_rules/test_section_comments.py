"""Tests for information.section_comments rule."""

from __future__ import annotations

from pathlib import Path

from slop._structural.section_comments import section_comment_kernel
from slop.models import RuleConfig, SlopConfig
from slop.rules.section_comments import run_section_comment_density

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _rc(threshold: int = 2) -> RuleConfig:
    return RuleConfig(enabled=True, severity="warning", params={"threshold": threshold})


def _sc(tmp_path: Path) -> SlopConfig:
    return SlopConfig(root=str(tmp_path))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

# Function with 3 section dividers — should fail at threshold=2
_MANY_DIVIDERS = '''\
def process_pipeline(data):
    # --- Step 1: validate ---
    if not data:
        return None
    validated = [x for x in data if x > 0]

    # --- Step 2: transform ---
    transformed = [x * 2 for x in validated]

    # --- Step 3: aggregate ---
    total = sum(transformed)
    return total
'''

# Function with 1 divider — should pass at threshold=2
_FEW_DIVIDERS = '''\
def prepare_data(items):
    # --- Filter ---
    clean = [x for x in items if x is not None]
    return clean
'''

# Function with no divider comments
_NO_DIVIDERS = '''\
def add_values(a, b, c):
    # This is a normal comment, not a divider
    result = a + b + c
    return result
'''

# Module-level divider outside any function — should NOT be attributed to a function
_MODULE_LEVEL_DIVIDER = '''\
# ==============================
# Module initialization
# ==============================

def simple_fn(x):
    return x + 1
'''


# ---------------------------------------------------------------------------
# Kernel tests
# ---------------------------------------------------------------------------


def test_kernel_detects_dividers_inside_function(tmp_path: Path):
    (tmp_path / "a.py").write_text(_MANY_DIVIDERS)
    result = section_comment_kernel(tmp_path)
    entry = next((e for e in result.entries if e.name == "process_pipeline"), None)
    assert entry is not None
    assert entry.divider_count == 3


def test_kernel_few_dividers_still_recorded(tmp_path: Path):
    (tmp_path / "a.py").write_text(_FEW_DIVIDERS)
    result = section_comment_kernel(tmp_path)
    # 1 divider should be recorded (below default threshold but kernel records all)
    entry = next((e for e in result.entries if e.name == "prepare_data"), None)
    assert entry is not None
    assert entry.divider_count == 1


def test_kernel_no_dividers_empty_entries(tmp_path: Path):
    (tmp_path / "a.py").write_text(_NO_DIVIDERS)
    result = section_comment_kernel(tmp_path)
    assert result.entries == []


def test_kernel_module_level_dividers_not_attributed_to_function(tmp_path: Path):
    """Module-level dividers must not be attributed to a function below them."""
    (tmp_path / "a.py").write_text(_MODULE_LEVEL_DIVIDER)
    result = section_comment_kernel(tmp_path)
    # simple_fn does not contain any dividers
    assert all(e.name != "simple_fn" or e.divider_count == 0
               for e in result.entries)


def test_kernel_divider_lines_are_correct(tmp_path: Path):
    (tmp_path / "a.py").write_text(_MANY_DIVIDERS)
    result = section_comment_kernel(tmp_path)
    entry = next((e for e in result.entries if e.name == "process_pipeline"), None)
    assert entry is not None
    assert len(entry.divider_lines) == entry.divider_count
    # All divider lines must be within the function span
    for ln in entry.divider_lines:
        assert entry.line <= ln <= entry.end_line


def test_kernel_different_divider_styles(tmp_path: Path):
    """Various divider styles must all be detected."""
    src = (
        "def mixed_styles():\n"
        "    # --- dash ---\n"
        "    x = 1\n"
        "    # === equal ===\n"
        "    y = 2\n"
        "    # *** star ***\n"
        "    return x + y\n"
    )
    (tmp_path / "a.py").write_text(src)
    result = section_comment_kernel(tmp_path)
    entry = next((e for e in result.entries if e.name == "mixed_styles"), None)
    assert entry is not None
    assert entry.divider_count == 3


# ---------------------------------------------------------------------------
# Rule wrapper tests
# ---------------------------------------------------------------------------


def test_rule_pass_few_dividers(tmp_path: Path):
    (tmp_path / "a.py").write_text(_FEW_DIVIDERS)
    result = run_section_comment_density(tmp_path, _rc(threshold=2), _sc(tmp_path))
    assert result.status == "pass"
    assert result.violations == []


def test_rule_fail_many_dividers(tmp_path: Path):
    (tmp_path / "a.py").write_text(_MANY_DIVIDERS)
    result = run_section_comment_density(tmp_path, _rc(threshold=2), _sc(tmp_path))
    assert result.status == "fail"
    assert len(result.violations) >= 1
    v = result.violations[0]
    assert v.rule == "information.section_comments"
    assert v.severity == "warning"
    assert v.value == 3


def test_rule_threshold_exactly_at_limit_passes(tmp_path: Path):
    (tmp_path / "a.py").write_text(_MANY_DIVIDERS)
    # threshold=3 means flag if count > 3; exactly 3 should pass
    result = run_section_comment_density(tmp_path, _rc(threshold=3), _sc(tmp_path))
    assert result.status == "pass"


def test_rule_violation_metadata_keys(tmp_path: Path):
    (tmp_path / "a.py").write_text(_MANY_DIVIDERS)
    result = run_section_comment_density(tmp_path, _rc(threshold=2), _sc(tmp_path))
    assert result.status == "fail"
    v = result.violations[0]
    assert "divider_lines" in v.metadata
    assert "language" in v.metadata


def test_rule_summary_keys(tmp_path: Path):
    (tmp_path / "a.py").write_text(_NO_DIVIDERS)
    result = run_section_comment_density(tmp_path, _rc(), _sc(tmp_path))
    for key in ("functions_analyzed", "files_searched", "violations", "threshold"):
        assert key in result.summary, f"missing key: {key}"
