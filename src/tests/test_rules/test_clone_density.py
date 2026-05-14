"""Tests for ``structural.duplication`` (Type-2 clone detection).

Covers Structure.clones() unit behaviour, the legacy ``_fingerprint`` /
``_leaf_types`` helpers (now hosted in ``slop.structure._clones``), and
the rule wrapper.
"""
from __future__ import annotations

from pathlib import Path

from slop.config.models import RuleConfig, SlopConfig
from slop.structure._clones import _fingerprint
from slop.structure.rules.clone_density import run_clone_density
from slop.tree.tree import Tree


def _structure(root: Path):
    t = Tree(root)
    t.scan()
    return t.structure


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

_DIFFERENT = """\
def compute_ratio(numerator, denominator):
    if denominator == 0:
        return None
    return numerator / denominator
"""


# ---------------------------------------------------------------------------
# Fingerprint helper
# ---------------------------------------------------------------------------


def test_fingerprint_same_structure_same_hash():
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
# Structure.clones() — clone detection
# ---------------------------------------------------------------------------


def test_clones_detects_clone_pair(tmp_path: Path):
    (tmp_path / "a.py").write_text(_CLONE_A)
    (tmp_path / "b.py").write_text(_CLONE_B)
    report = _structure(tmp_path).clones(min_leaf_nodes=5)
    assert report.functions_analyzed >= 2
    assert len(report.clusters) >= 1
    assert report.clone_fraction > 0.0


def test_clones_no_clones_for_different_functions(tmp_path: Path):
    (tmp_path / "a.py").write_text(_CLONE_A)
    (tmp_path / "b.py").write_text(_DIFFERENT)
    report = _structure(tmp_path).clones(min_leaf_nodes=5)
    assert all(c.size < 2 for c in report.clusters)


def test_clones_cluster_members_have_correct_files(tmp_path: Path):
    (tmp_path / "a.py").write_text(_CLONE_A)
    (tmp_path / "b.py").write_text(_CLONE_B)
    report = _structure(tmp_path).clones(min_leaf_nodes=5)
    cluster = next((c for c in report.clusters if c.size >= 2), None)
    assert cluster is not None
    names = {Path(m.file).name for m in cluster.members}
    assert "a.py" in names
    assert "b.py" in names


def test_clones_min_leaf_nodes_filters_trivial_functions(tmp_path: Path):
    """Very short functions should be excluded when min_leaf_nodes is high."""
    src = "def f(): pass\ndef g(): pass\n"
    (tmp_path / "a.py").write_text(src)
    report = _structure(tmp_path).clones(min_leaf_nodes=100)
    assert len(report.clusters) == 0


def test_clones_same_file_clone_detected(tmp_path: Path):
    src = _CLONE_A + "\n" + _CLONE_B
    (tmp_path / "a.py").write_text(src)
    report = _structure(tmp_path).clones(min_leaf_nodes=5)
    assert len(report.clusters) >= 1


def test_clones_returns_sorted_clusters(tmp_path: Path):
    (tmp_path / "a.py").write_text(_CLONE_A)
    (tmp_path / "b.py").write_text(_CLONE_B)
    report = _structure(tmp_path).clones(min_leaf_nodes=5)
    sizes = [c.size for c in report.clusters]
    assert sizes == sorted(sizes, reverse=True)


# ---------------------------------------------------------------------------
# Rule wrapper
# ---------------------------------------------------------------------------


def test_rule_pass_no_clones(tmp_path: Path):
    (tmp_path / "a.py").write_text(_CLONE_A)
    (tmp_path / "b.py").write_text(_DIFFERENT)
    result = run_clone_density(_structure(tmp_path), _rc(threshold=0.05), _sc(tmp_path))
    assert result.status == "pass"
    assert result.violations == []


def test_rule_fail_clone_pair(tmp_path: Path):
    (tmp_path / "a.py").write_text(_CLONE_A)
    (tmp_path / "b.py").write_text(_CLONE_B)
    result = run_clone_density(_structure(tmp_path), _rc(threshold=0.0), _sc(tmp_path))
    assert result.status == "fail"
    assert any(v.rule == "structural.duplication" for v in result.violations)


def test_rule_violation_contains_fingerprint(tmp_path: Path):
    (tmp_path / "a.py").write_text(_CLONE_A)
    (tmp_path / "b.py").write_text(_CLONE_B)
    result = run_clone_density(_structure(tmp_path), _rc(threshold=0.0), _sc(tmp_path))
    fingerprinted = [v for v in result.violations if v.metadata.get("fingerprint")]
    assert fingerprinted


def test_rule_summary_keys(tmp_path: Path):
    (tmp_path / "a.py").write_text(_CLONE_A)
    result = run_clone_density(_structure(tmp_path), _rc(), _sc(tmp_path))
    for key in ("functions_analyzed", "clone_clusters", "clone_fraction", "threshold"):
        assert key in result.summary, f"missing key: {key}"
