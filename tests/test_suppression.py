"""Inline suppression: a `slop: ignore` marker on the line a violation is reported at drops
it, like `noqa`. A bracketed list narrows it to named rules; a family name covers its rules."""
from __future__ import annotations

from pathlib import Path

import pytest

from slop.config import AnalysisConfig, RuleConfig
from slop.dispatch import Dispatcher
from slop.rules import RULE_REGISTRY
from slop.scope import scan_corpus

BODY = "    if v:\n        return 1\n    if v > 2:\n        return 2\n    return 3\n"


def _fired(tmp_path: Path) -> set[str]:
    """Rules reported once cyclomatic and cognitive both trip on every callable."""
    cfg = AnalysisConfig.defaults(RULE_REGISTRY)
    rules = {**cfg.rules,
             "complexity.cyclomatic": RuleConfig("complexity.cyclomatic", thresholds={"callable": 1}),
             "complexity.cognitive": RuleConfig("complexity.cognitive", thresholds={"callable": 1})}
    cfg = AnalysisConfig(rules)
    report = Dispatcher(RULE_REGISTRY, cfg).run(scan_corpus(tmp_path, cfg))
    return {v.rule for v in report.violations if v.rule.startswith("complexity.")}


def _py(tmp_path: Path, comment: str, *, on_def: bool = True) -> set[str]:
    head = f"def f(v):{comment}\n" if on_def else f"def f(v):\n{BODY.splitlines()[0]}{comment}\n"
    rest = BODY if on_def else "\n".join(BODY.splitlines()[1:]) + "\n"
    (tmp_path / "m.py").write_text(head + rest)
    return _fired(tmp_path)


BOTH = {"complexity.cyclomatic", "complexity.cognitive"}


def test_without_a_marker_both_rules_fire(tmp_path: Path):
    assert _py(tmp_path, "") == BOTH


def test_a_bare_marker_drops_every_violation_on_that_line(tmp_path: Path):
    assert _py(tmp_path, "  # slop: ignore") == set()


def test_a_named_rule_drops_only_that_rule(tmp_path: Path):
    assert _py(tmp_path, "  # slop: ignore[complexity.cyclomatic]") == {"complexity.cognitive"}


def test_several_names_in_one_marker(tmp_path: Path):
    assert _py(tmp_path, "  # slop: ignore[complexity.cyclomatic, complexity.cognitive]") == set()


def test_a_family_name_drops_every_rule_in_the_family(tmp_path: Path):
    assert _py(tmp_path, "  # slop: ignore[complexity]") == set()


def test_a_family_prefix_must_end_at_a_dot(tmp_path: Path):
    assert _py(tmp_path, "  # slop: ignore[complex]") == BOTH


def test_a_different_rule_name_does_not_drop(tmp_path: Path):
    assert _py(tmp_path, "  # slop: ignore[structure.god-module]") == BOTH


def test_a_marker_on_another_line_does_not_drop(tmp_path: Path):
    assert _py(tmp_path, "  # slop: ignore", on_def=False) == BOTH


def test_a_marker_in_a_double_slash_comment(tmp_path: Path):
    (tmp_path / "m.ts").write_text(
        "function f(v) { // slop: ignore[complexity.cyclomatic]\n"
        "  if (v) { return 1 }\n  if (v > 2) { return 2 }\n  return 3\n}\n")
    assert _fired(tmp_path) == {"complexity.cognitive"}


def test_a_bare_marker_in_a_double_slash_comment(tmp_path: Path):
    (tmp_path / "m.ts").write_text(
        "function f(v) { // slop: ignore\n"
        "  if (v) { return 1 }\n  if (v > 2) { return 2 }\n  return 3\n}\n")
    assert _fired(tmp_path) == set()


@pytest.mark.parametrize("marker", ["#slop:ignore", "# slop:  ignore"])
def test_whitespace_around_the_colon_is_tolerated(tmp_path: Path, marker: str):
    assert _py(tmp_path, "  " + marker) == set()


def test_suppression_applies_per_violation_not_per_file(tmp_path: Path):
    (tmp_path / "m.py").write_text(
        "def quiet(v):  # slop: ignore\n" + BODY + "\ndef loud(v):\n" + BODY)
    cfg = AnalysisConfig({"complexity.cyclomatic": RuleConfig(
        "complexity.cyclomatic", thresholds={"callable": 1})})
    report = Dispatcher(RULE_REGISTRY, cfg).run(scan_corpus(tmp_path, cfg))
    assert [v.line for v in report.violations] == [8]
