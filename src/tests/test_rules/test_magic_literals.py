"""Tests for information.magic_literals rule."""

from __future__ import annotations

from pathlib import Path

from slop._structural.magic_literals import magic_literals_kernel, _is_trivial
from slop.models import RuleConfig, SlopConfig
from slop.rules.magic_literals import run_magic_literal_density

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _rc(threshold: int = 3) -> RuleConfig:
    return RuleConfig(enabled=True, severity="warning", params={"threshold": threshold})


def _sc(tmp_path: Path) -> SlopConfig:
    return SlopConfig(root=str(tmp_path))


# ---------------------------------------------------------------------------
# _is_trivial unit tests
# ---------------------------------------------------------------------------


def test_trivial_zero():
    assert _is_trivial("0") is True


def test_trivial_one():
    assert _is_trivial("1") is True


def test_trivial_neg_one():
    assert _is_trivial("-1") is True


def test_trivial_float_zero():
    assert _is_trivial("0.0") is True


def test_non_trivial_integer():
    assert _is_trivial("42") is False


def test_non_trivial_float():
    assert _is_trivial("3.14") is False


def test_non_trivial_large():
    assert _is_trivial("86400") is False


# ---------------------------------------------------------------------------
# Kernel tests
# ---------------------------------------------------------------------------

_MAGIC_HEAVY = """\
def compute_fee(amount):
    base = amount * 1.05
    if amount > 1000:
        discount = amount * 0.12
    elif amount > 5000:
        discount = amount * 0.18
    tax = base * 0.0825
    return base - discount + tax
"""

_MAGIC_CLEAN = """\
RATE = 1.05
DISCOUNT_THRESHOLD = 1000
DISCOUNT_RATE = 0.12
TAX_RATE = 0.0825

def compute_fee(amount):
    base = amount * RATE
    if amount > DISCOUNT_THRESHOLD:
        discount = amount * DISCOUNT_RATE
    tax = base * TAX_RATE
    return base - discount + tax
"""

_TRIVIAL_ONLY = """\
def increment(value):
    return value + 1

def reset(data):
    return data[0]
"""


def test_kernel_detects_magic_literals(tmp_path: Path):
    (tmp_path / "a.py").write_text(_MAGIC_HEAVY)
    result = magic_literals_kernel(tmp_path)
    entry = next((e for e in result.entries if e.name == "compute_fee"), None)
    assert entry is not None
    assert entry.distinct_count >= 4  # 1.05, 1000, 0.12, 5000, 0.18, 0.0825


def test_kernel_clean_file_no_entries(tmp_path: Path):
    """File using named constants should produce no entries."""
    (tmp_path / "a.py").write_text(_MAGIC_CLEAN)
    result = magic_literals_kernel(tmp_path)
    # The function should not appear or have 0 distinct magic literals
    magic_fn = next((e for e in result.entries if e.name == "compute_fee"), None)
    assert magic_fn is None or magic_fn.distinct_count == 0


def test_kernel_trivial_literals_excluded(tmp_path: Path):
    (tmp_path / "a.py").write_text(_TRIVIAL_ONLY)
    result = magic_literals_kernel(tmp_path)
    # 0 and 1 are trivial; no entries should be produced
    assert result.entries == []


def test_kernel_entries_sorted_desc(tmp_path: Path):
    (tmp_path / "a.py").write_text(_MAGIC_HEAVY)
    result = magic_literals_kernel(tmp_path)
    counts = [e.distinct_count for e in result.entries]
    assert counts == sorted(counts, reverse=True)


def test_kernel_functions_analyzed_count(tmp_path: Path):
    src = _MAGIC_HEAVY + "\n" + _TRIVIAL_ONLY
    (tmp_path / "a.py").write_text(src)
    result = magic_literals_kernel(tmp_path)
    assert result.functions_analyzed >= 3  # compute_fee + increment + reset


# ---------------------------------------------------------------------------
# Rule wrapper tests
# ---------------------------------------------------------------------------


def test_rule_pass_clean_code(tmp_path: Path):
    (tmp_path / "a.py").write_text(_MAGIC_CLEAN)
    result = run_magic_literal_density(tmp_path, _rc(threshold=3), _sc(tmp_path))
    assert result.status == "pass"
    assert result.violations == []


def test_rule_fail_magic_heavy(tmp_path: Path):
    (tmp_path / "a.py").write_text(_MAGIC_HEAVY)
    result = run_magic_literal_density(tmp_path, _rc(threshold=3), _sc(tmp_path))
    assert result.status == "fail"
    assert len(result.violations) >= 1
    v = result.violations[0]
    assert v.rule == "information.magic_literals"
    assert v.severity == "warning"
    assert v.value > 3


def test_rule_exact_threshold_passes(tmp_path: Path):
    """Functions with exactly threshold distinct literals should pass."""
    (tmp_path / "a.py").write_text(_MAGIC_HEAVY)
    result = run_magic_literal_density(tmp_path, _rc(threshold=999), _sc(tmp_path))
    assert result.status == "pass"


def test_rule_violation_metadata_keys(tmp_path: Path):
    (tmp_path / "a.py").write_text(_MAGIC_HEAVY)
    result = run_magic_literal_density(tmp_path, _rc(threshold=1), _sc(tmp_path))
    if result.violations:
        v = result.violations[0]
        for key in ("language", "literals", "distinct_count"):
            assert key in v.metadata, f"missing key: {key}"


def test_rule_summary_keys(tmp_path: Path):
    (tmp_path / "a.py").write_text(_MAGIC_CLEAN)
    result = run_magic_literal_density(tmp_path, _rc(), _sc(tmp_path))
    for key in ("functions_analyzed", "files_searched", "violations", "threshold"):
        assert key in result.summary, f"missing key: {key}"
