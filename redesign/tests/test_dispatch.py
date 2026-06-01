"""Dispatcher — altitude-driven execution, the zero-visited safeguard, exit
codes, and that all three representative rules fire (one per ontology cell)."""
from __future__ import annotations

from pathlib import Path

from slop.config import AnalysisConfig, RuleConfig
from slop.dispatch import Dispatcher
from slop.finding import Action, Disposition, Severity
from slop.model import scan_corpus
from slop.rules import RULE_REGISTRY

# Two disjoint call-clusters, each of >=2 mutually-calling functions (so they
# survive the min_island_size singleton filter); each entry has a branch so
# cyclomatic > 1; enough distinct identifiers for the vocabulary floor.
TWO_ISLANDS = '''\
def alpha(first_value):
    if first_value:
        return alpha_helper(first_value)
    return 0

def alpha_helper(value):
    return value + 1

def beta(second_value):
    while second_value > 0:
        second_value = beta_helper(second_value)
    return second_value

def beta_helper(value):
    return value - 1
'''


def _tuned_config() -> AnalysisConfig:
    """Thresholds lowered so the tiny fixture deterministically trips each rule."""
    return AnalysisConfig({
        "complexity.cyclomatic": RuleConfig(
            name="complexity.cyclomatic", severity=Severity.ERROR,
            thresholds={"callable": 1}),
        "structure.call-islands": RuleConfig(
            name="structure.call-islands", params={"min_islands": 2, "min_functions": 2}),
        "vocabulary": RuleConfig(
            name="vocabulary", severity=Severity.INFO,
            params={"package_min_distinct": 1, "top_tokens": 5}),
    })


def _run(tmp_path: Path, source: str, config: AnalysisConfig):
    (tmp_path / "sample.py").write_text(source)
    corpus = scan_corpus(tmp_path, config=config)
    return Dispatcher(RULE_REGISTRY, config).run(corpus)


def test_all_three_rules_fire(tmp_path: Path):
    report = _run(tmp_path, TWO_ISLANDS, _tuned_config())
    fired = {f.rule for f in report.findings}
    assert fired == {"complexity.cyclomatic", "structure.call-islands", "vocabulary"}


def test_every_ontology_cell_is_exercised(tmp_path: Path):
    report = _run(tmp_path, TWO_ISLANDS, _tuned_config())
    dispositions = {f.disposition for f in report.findings}
    actions = {f.action for f in report.findings}
    assert dispositions == {Disposition.VERDICT, Disposition.OBSERVATION}
    assert Action.REDUCE_COMPLEXITY in actions   # ordinary verdict
    assert Action.REVIEW in actions              # deferred-remedy verdict
    assert Action.INVESTIGATE in actions         # observation


def test_review_finding_is_warning_pinned(tmp_path: Path):
    report = _run(tmp_path, TWO_ISLANDS, _tuned_config())
    review = [f for f in report.findings if f.rule == "structure.call-islands"]
    assert review and all(f.severity is Severity.WARNING for f in review)
    assert all(f.disposition is Disposition.VERDICT for f in review)


def test_error_verdict_drives_exit_code_one(tmp_path: Path):
    report = _run(tmp_path, TWO_ISLANDS, _tuned_config())
    assert any(f.severity is Severity.ERROR for f in report.findings)
    assert report.exit_code() == 1


def test_observations_alone_do_not_gate(tmp_path: Path):
    # vocabulary only — an observation must never produce a non-zero exit.
    cfg = AnalysisConfig({"vocabulary": RuleConfig(
        name="vocabulary", severity=Severity.INFO, params={"package_min_distinct": 1})})
    report = _run(tmp_path, TWO_ISLANDS, cfg)
    assert report.observations()
    assert report.exit_code() == 0


def test_zero_visited_safeguard(tmp_path: Path):
    # A module with no callables/classes: cyclomatic (altitude {callable, class})
    # visits nothing and must be surfaced, not pass silently as clean.
    cfg = AnalysisConfig({"complexity.cyclomatic": RuleConfig(
        name="complexity.cyclomatic", thresholds={"callable": 1, "class": 1})})
    report = _run(tmp_path, "x = 1\ny = 2\n", cfg)
    assert "complexity.cyclomatic" in report.zero_visited
