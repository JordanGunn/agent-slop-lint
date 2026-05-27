"""Tests for slop orphans rule (view-native dead-code candidate audit)."""

from __future__ import annotations

from pathlib import Path

from slop.linter.rule import Rule
from slop.config import Config
from slop.linter.rules.orphans import run_orphans
from slop.tree.tree import Tree


def _structure(root: Path):
    tree = Tree(root); tree.scan()
    return tree.structure


def _rc(min_confidence: str = "high") -> Rule:
    return Rule(
        enabled=True, severity="warning",
        params={"min_confidence": min_confidence},
    )


def _sc(root: Path) -> Config:
    return Config(root=str(root))


def test_unreferenced_function_flagged_at_medium_confidence(tmp_path: Path):
    """An unreferenced function with a long descriptive name is medium
    confidence in Python (dynamic-language penalty)."""
    (tmp_path / "orphan.py").write_text(
        "def absolutely_unreferenced_helper_function():\n    return 1\n"
    )
    result = run_orphans(_structure(tmp_path), _rc(min_confidence="medium"), _sc(tmp_path))
    assert result.status == "fail"
    assert any(
        v.symbol == "absolutely_unreferenced_helper_function"
        for v in result.violations
    )


def test_referenced_function_not_flagged(tmp_path: Path):
    """Even when listed in a second file, an external reference suppresses
    the candidate."""
    (tmp_path / "core.py").write_text(
        "def used_helper_function():\n    return 1\n"
    )
    (tmp_path / "caller.py").write_text(
        "from core import used_helper_function\nused_helper_function()\n"
    )
    result = run_orphans(_structure(tmp_path), _rc(min_confidence="medium"), _sc(tmp_path))
    assert all(v.symbol != "used_helper_function" for v in result.violations)


def test_min_confidence_filters(tmp_path: Path):
    """``min_confidence=high`` excludes medium-confidence candidates."""
    (tmp_path / "x.py").write_text(
        "def absolutely_unreferenced_helper_function():\n    return 1\n"
    )
    result = run_orphans(_structure(tmp_path), _rc(min_confidence="high"), _sc(tmp_path))
    # Python downgrades to medium → high filter excludes it.
    assert all(
        v.symbol != "absolutely_unreferenced_helper_function"
        for v in result.violations
    )


def test_short_names_skipped(tmp_path: Path):
    """Symbols below the 4-character minimum are not analysed."""
    (tmp_path / "y.py").write_text("def go():\n    return 1\n")
    result = run_orphans(_structure(tmp_path), _rc(min_confidence="low"), _sc(tmp_path))
    assert all(v.symbol != "go" for v in result.violations)
