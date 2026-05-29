"""Tests for lexical.confusion (v1.2.0+).

Grab-bag detection via disjoint call-islands: a file whose top-level
functions partition into >= 2 connected components of shared-callee
redundancy. Supersedes the earlier first-parameter-receiver model.
"""
from __future__ import annotations

from pathlib import Path

from slop.linter.rule import Rule
from slop.config import Config
from slop.linter.rules import confusion as _confusion_rule
from slop.tree.tree import Tree


def _lexicon(root: Path):
    t = Tree(root)
    t.scan()
    return t.lexicon


def _slop() -> Config:
    return Config(rules={}, languages=["python"])


def _rc(**params) -> Rule:
    return Rule(enabled=True, severity="warning", params=params)


def test_confusion_flags_disconnected_grab_bag(tmp_path: Path):
    """Two call-islands with NO bridging coordinator → deterministic split."""
    (tmp_path / "output.py").write_text(
        # Island A: three functions sharing {alpha_load, alpha_parse, alpha_emit}
        "def handle_first(x):\n"
        "    alpha_load(x); alpha_parse(x); alpha_emit(x)\n"
        "def handle_second(x):\n"
        "    alpha_load(x); alpha_parse(x); alpha_emit(x)\n"
        "def handle_third(x):\n"
        "    alpha_load(x); alpha_parse(x); alpha_emit(x)\n"
        # Island B: two functions sharing {beta_open, beta_read, beta_close}
        "def serve_first(y):\n"
        "    beta_open(y); beta_read(y); beta_close(y)\n"
        "def serve_second(y):\n"
        "    beta_open(y); beta_read(y); beta_close(y)\n"
    )
    result = _confusion_rule.run(_lexicon(tmp_path), _rc(), _slop())
    assert result.status == "fail"
    assert len(result.violations) == 1
    v = result.violations[0]
    assert v.symbol is not None and "output.py" in v.symbol
    # coordinator test passed (disconnected) → deterministic split
    assert v.action is not None and v.action.value == "split-module"
    islands = v.metadata["islands"]
    assert len(islands) == 2
    assert v.metadata["call_components"] >= 2
    members = {name for isl in islands for name in isl}
    assert {"handle_first", "serve_first"} <= members


def test_confusion_suppresses_coordinated_pipeline(tmp_path: Path):
    """Two islands joined by a bridging coordinator → cohesive pipeline, suppressed."""
    (tmp_path / "pipeline.py").write_text(
        # Island A
        "def stage_load(x):\n    alpha_one(x); alpha_two(x); alpha_three(x)\n"
        "def stage_parse(x):\n    alpha_one(x); alpha_two(x); alpha_three(x)\n"
        # Island B
        "def stage_emit(y):\n    beta_one(y); beta_two(y); beta_three(y)\n"
        "def stage_flush(y):\n    beta_one(y); beta_two(y); beta_three(y)\n"
        # Coordinator bridging both islands → single call-component
        "def run_pipeline(z):\n"
        "    stage_load(z); stage_parse(z); stage_emit(z); stage_flush(z)\n"
    )
    result = _confusion_rule.run(_lexicon(tmp_path), _rc(), _slop())
    assert result.status == "pass"


def test_confusion_passes_for_single_island(tmp_path: Path):
    """File with one cohesive call-island (one cluster) doesn't fire."""
    (tmp_path / "renderer.py").write_text(
        "def fmt_a(r):\n    shared_one(r); shared_two(r); shared_three(r)\n"
        "def fmt_b(r):\n    shared_one(r); shared_two(r); shared_three(r)\n"
        "def fmt_c(r):\n    shared_one(r); shared_two(r); shared_three(r)\n"
        "def fmt_d(r):\n    shared_one(r); shared_two(r); shared_three(r)\n"
        "def fmt_e(r):\n    shared_one(r); shared_two(r); shared_three(r)\n"
    )
    result = _confusion_rule.run(_lexicon(tmp_path), _rc(), _slop())
    assert result.status == "pass"


def test_confusion_skips_small_file(tmp_path: Path):
    """Two islands below min_functions don't fire."""
    (tmp_path / "tiny.py").write_text(
        "def fa(x):\n    aa_one(x); aa_two(x); aa_three(x)\n"
        "def fb(x):\n    aa_one(x); aa_two(x); aa_three(x)\n"
        "def ga(y):\n    bb_one(y); bb_two(y); bb_three(y)\n"
        "def gb(y):\n    bb_one(y); bb_two(y); bb_three(y)\n"
    )
    result = _confusion_rule.run(_lexicon(tmp_path), _rc(min_functions=10), _slop())
    assert result.status == "pass"
