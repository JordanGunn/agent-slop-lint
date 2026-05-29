"""Tests for the ``vocabulary`` rule — claim-free observation emission.

The rule must emit an OBSERVATION (not a verdict): it carries evidence +
a narration, never lands in ``violations``, and never affects the run
verdict. These tests lock that contract so a future change can't silently
turn an instrument into a build-failing rule.
"""
from __future__ import annotations

from pathlib import Path

from slop.config import Config
from slop.linter.linter import Linter
from slop.linter.rule import Rule
from slop.linter.rules import vocabulary
from slop.linter.slop import Action, Disposition
from slop.tree.tree import Tree


def _tree(root: Path):
    t = Tree(root)
    t.scan()
    return t


def _rc() -> Rule:
    return Rule(enabled=True, severity="info", params={"top_tokens": 15})


def _sc(root: Path) -> Config:
    return Config(root=str(root))


def _corpus(root: Path) -> None:
    (root / "m.py").write_text(
        "def load_node(node):\n    return node\n"
        "def save_node(node):\n    return node\n"
        "def walk_tree(tree):\n    return tree\n"
    )


class TestObservationContract:
    def test_emits_observation_not_violation(self, tmp_path: Path):
        _corpus(tmp_path)
        result = vocabulary.run(_tree(tmp_path), _rc(), _sc(tmp_path))
        assert result.status == "pass"
        assert result.violations == []
        assert len(result.observations) == 1

    def test_observation_shape(self, tmp_path: Path):
        _corpus(tmp_path)
        ob = vocabulary.run(_tree(tmp_path), _rc(), _sc(tmp_path)).observations[0]
        assert ob.rule == "vocabulary"
        assert ob.disposition == Disposition.OBSERVATION
        assert ob.action == Action.INVESTIGATE
        assert ob.severity == "info"
        assert ob.prescription is None
        assert ob.evidence is not None
        assert ob.evidence.kind == "token-distribution"
        assert ob.message  # narration present

    def test_summary_reports_a_count(self, tmp_path: Path):
        _corpus(tmp_path)
        result = vocabulary.run(_tree(tmp_path), _rc(), _sc(tmp_path))
        # tokens_analyzed must be > 0 so the zero-checked safeguard stays quiet
        assert result.summary["tokens_analyzed"] > 0

    def test_within_namespace_evidence_present(self, tmp_path: Path):
        # two packages, each with enough vocabulary to clear a low floor
        (tmp_path / "pkg_a").mkdir()
        (tmp_path / "pkg_a" / "m.py").write_text(
            "def aa_one(): pass\ndef aa_two(): pass\ndef aa_three(): pass\n"
        )
        (tmp_path / "pkg_b").mkdir()
        (tmp_path / "pkg_b" / "m.py").write_text(
            "def node_load(node): return node\ndef node_save(node): return node\n"
        )
        rc = Rule(enabled=True, severity="info",
                  params={"top_tokens": 15, "package_min_distinct": 2})
        ob = vocabulary.run(_tree(tmp_path), rc, _sc(tmp_path)).observations[0]
        data = ob.evidence.data
        assert "per_package" in data
        assert data["package_min_distinct"] == 2
        pkgs = {row["package"] for row in data["per_package"]}
        assert {"pkg_a", "pkg_b"} <= pkgs
        # narration appended the per-package listing
        assert "Per-package" in ob.message

    def test_empty_corpus_emits_nothing(self, tmp_path: Path):
        (tmp_path / "empty.py").write_text("\n")
        result = vocabulary.run(_tree(tmp_path), _rc(), _sc(tmp_path))
        assert result.observations == []
        assert result.summary["tokens_analyzed"] == 0

    def test_cross_view_across_axis_present(self, tmp_path: Path):
        _corpus(tmp_path)
        ob = vocabulary.run(_tree(tmp_path), _rc(), _sc(tmp_path)).observations[0]
        # the across-axis (needs the Structure import graph) flowed through
        assert "concept_ownership" in ob.evidence.data
        assert "Concept ownership" in ob.message

    def test_rule_is_cross_view(self):
        # the dispatcher passes the whole Tree only when view == "tree"
        assert vocabulary.RULE.view == "tree"


class TestVerdictUnaffected:
    def test_observation_does_not_fail_the_build(self, tmp_path: Path):
        _corpus(tmp_path)
        result = Linter(_sc(tmp_path)).run(filter_rule="vocabulary")
        assert result.verdict == "pass"
        assert result.slop_count == 0
        assert result.observation_count == 1

    def test_observation_in_json_output(self, tmp_path: Path):
        _corpus(tmp_path)
        out = Linter(_sc(tmp_path)).run(filter_rule="vocabulary").json()
        assert out["summary"]["observation_count"] == 1
        obs = out["rules"]["vocabulary"]["observations"]
        assert len(obs) == 1
        assert obs[0]["disposition"] == "observation"
        assert obs[0]["evidence"]["kind"] == "token-distribution"
