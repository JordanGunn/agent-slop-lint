"""Tests for structural.clone_density rule and clone_density_kernel."""

from __future__ import annotations

from pathlib import Path

from slop._structural.clone_density import (
    CloneEntry,
    clone_density_kernel,
    _fingerprint,
    _collect_leaf_types,
)
from slop.models import RuleConfig, SlopConfig
from slop.rules.clone_density import run_clone_density


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _rc(**overrides) -> RuleConfig:
    params = {"threshold": 0.05, "min_leaf_nodes": 5, "min_cluster_size": 2}
    params.update(overrides)
    return RuleConfig(enabled=True, severity="warning", params=params)


def _sc(tmp_path: Path) -> SlopConfig:
    return SlopConfig(root=str(tmp_path))


# Two structurally identical functions — same shape, different names
_CLONE_A = """\
def process_values(items, factor):
    total = 0
    for item in items:
        total = total + item * factor
    return total
"""

_CLONE_B = """\
def aggregate_scores(entries, multiplier):
    result = 0
    for entry in entries:
        result = result + entry * multiplier
    return result
"""

# A function with a clearly different structure
_DIFFERENT = """\
def compute_ratio(numerator, denominator):
    if denominator == 0:
        return None
    return numerator / denominator
"""


# ---------------------------------------------------------------------------
# Fingerprint unit tests
# ---------------------------------------------------------------------------


def test_fingerprint_same_structure_same_hash():
    """Two functions with the same structure must produce the same hash."""
    # We cannot test tree-sitter fingerprinting without parsing, but we can
    # test the hash function directly with identical leaf sequences.
    leaves = ["def", "identifier", "parameters", "block", "return", "integer"]
    h1 = _fingerprint(leaves)
    h2 = _fingerprint(leaves)
    assert h1 == h2
    assert len(h1) == 12


def test_fingerprint_different_structure_different_hash():
    leaves_a = ["def", "identifier", "parameters", "block", "return", "integer"]
    leaves_b = ["def", "identifier", "parameters", "block", "if", "return"]
    assert _fingerprint(leaves_a) != _fingerprint(leaves_b)


# ---------------------------------------------------------------------------
# Kernel — clone detection
# ---------------------------------------------------------------------------


def test_kernel_detects_clone_pair(tmp_path: Path):
    """Two structurally identical functions in separate files must form a cluster."""
    (tmp_path / "a.py").write_text(_CLONE_A)
    (tmp_path / "b.py").write_text(_CLONE_B)
    result = clone_density_kernel(tmp_path, min_leaf_nodes=5)
    assert result.functions_analyzed >= 2
    # The two clones must end up in a cluster
    assert len(result.clusters) >= 1
    assert result.clone_fraction > 0.0


def test_kernel_no_clones_for_different_functions(tmp_path: Path):
    (tmp_path / "a.py").write_text(_CLONE_A)
    (tmp_path / "b.py").write_text(_DIFFERENT)
    result = clone_density_kernel(tmp_path, min_leaf_nodes=5)
    # The two functions have different structures → no cluster of size ≥ 2
    assert all(c.size < 2 for c in result.clusters)


def test_kernel_cluster_members_have_correct_files(tmp_path: Path):
    (tmp_path / "a.py").write_text(_CLONE_A)
    (tmp_path / "b.py").write_text(_CLONE_B)
    result = clone_density_kernel(tmp_path, min_leaf_nodes=5)
    cluster = next((c for c in result.clusters if c.size >= 2), None)
    assert cluster is not None
    files = {m.file for m in cluster.members}
    assert "a.py" in files
    assert "b.py" in files


def test_kernel_min_leaf_nodes_filters_trivial_functions(tmp_path: Path):
    """Very short functions should be excluded when min_leaf_nodes is high."""
    src = "def f(): pass\ndef g(): pass\n"
    (tmp_path / "a.py").write_text(src)
    # With a high min_leaf_nodes, both trivial functions are skipped
    result = clone_density_kernel(tmp_path, min_leaf_nodes=100)
    assert len(result.clusters) == 0


def test_kernel_same_file_clone_detected(tmp_path: Path):
    """Clones in the same file must also be detected."""
    src = _CLONE_A + "\n" + _CLONE_B
    (tmp_path / "a.py").write_text(src)
    result = clone_density_kernel(tmp_path, min_leaf_nodes=5)
    assert len(result.clusters) >= 1


def test_kernel_returns_sorted_clusters(tmp_path: Path):
    """Clusters must be sorted by size descending."""
    (tmp_path / "a.py").write_text(_CLONE_A)
    (tmp_path / "b.py").write_text(_CLONE_B)
    result = clone_density_kernel(tmp_path, min_leaf_nodes=5)
    sizes = [c.size for c in result.clusters]
    assert sizes == sorted(sizes, reverse=True)


def test_kernel_files_searched_count(tmp_path: Path):
    (tmp_path / "a.py").write_text(_CLONE_A)
    (tmp_path / "b.py").write_text(_CLONE_B)
    result = clone_density_kernel(tmp_path, min_leaf_nodes=5)
    assert result.files_searched == 2


# ---------------------------------------------------------------------------
# Rule wrapper
# ---------------------------------------------------------------------------


def test_rule_pass_no_clones(tmp_path: Path):
    (tmp_path / "a.py").write_text(_CLONE_A)
    (tmp_path / "b.py").write_text(_DIFFERENT)
    result = run_clone_density(tmp_path, _rc(threshold=0.05), _sc(tmp_path))
    assert result.status == "pass"
    assert result.violations == []


def test_rule_fail_clone_pair(tmp_path: Path):
    (tmp_path / "a.py").write_text(_CLONE_A)
    (tmp_path / "b.py").write_text(_CLONE_B)
    # Set threshold=0 so any clone fraction fails
    result = run_clone_density(tmp_path, _rc(threshold=0.0), _sc(tmp_path))
    assert result.status == "fail"
    assert any(v.rule == "structural.duplication" for v in result.violations)


def test_rule_violation_contains_fingerprint(tmp_path: Path):
    (tmp_path / "a.py").write_text(_CLONE_A)
    (tmp_path / "b.py").write_text(_CLONE_B)
    result = run_clone_density(tmp_path, _rc(threshold=0.0), _sc(tmp_path))
    cluster_violations = [v for v in result.violations if v.metadata.get("fingerprint")]
    assert cluster_violations, "expected at least one violation with fingerprint metadata"


def test_rule_summary_keys(tmp_path: Path):
    (tmp_path / "a.py").write_text(_CLONE_A)
    result = run_clone_density(tmp_path, _rc(), _sc(tmp_path))
    for key in ("functions_analyzed", "files_searched", "clone_clusters",
                "clone_fraction", "threshold"):
        assert key in result.summary, f"missing key: {key}"
