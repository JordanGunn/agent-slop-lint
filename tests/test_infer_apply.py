"""apply: validate verdicts, route them into the ledger, settle a report and say where each ruling stands."""
from __future__ import annotations

from pathlib import Path

import pytest

from slop.config import AnalysisConfig
from slop.dispatch import Dispatcher
from slop.infer.apply.route import route
from slop.infer.apply.settle import settle
from slop.infer.apply.validate import validate
from slop.infer.contract import SCHEMA_VERSION, Location, Outcome, Question, Residue, RubricRef, Status, Verdict, Verdicts
from slop.infer.ledger.jsonl import JsonlLedger
from slop.infer.source.finding import FindingSource
from slop.infer.source.interface import Analysis
from slop.rules import RULE_REGISTRY
from slop.scope import scan_corpus

TWO_GROUPS = "class A:\n    def f(self):\n        return self.a * 2\n\n    def g(self):\n        return self.b * 2\n"


def _item(item_id: str = "a1", outcomes: tuple[Outcome, ...] = tuple(Outcome)) -> Residue:
    return Residue(id=item_id, rule="class-cohesion", subject="m.A", locations=(Location(path="m.py", first_line=1, last_line=2),),
                   question=Question(id="q", text="q?", outcomes=outcomes),
                   rubric=RubricRef(command="slop infer references rubrics/class-cohesion", version="rv"),
                   fingerprint="fp", status=Status.NONE)


def _verdicts(*triples: tuple[str, Outcome, str]) -> Verdicts:
    return Verdicts(version=SCHEMA_VERSION, verdicts=tuple(Verdict(id=i, outcome=o, reason=r) for i, o, r in triples))


def test_a_verdict_for_a_listed_finding_with_an_allowed_outcome_is_accepted():
    assert validate(_verdicts(("a1", Outcome.CLEAR, "ok")), {"a1": _item()}) == ()


def test_unknown_ids_disallowed_outcomes_and_repeated_ids_are_rejected_with_a_reason():
    residue = {"a1": _item("a1", outcomes=(Outcome.CLEAR, Outcome.DEFER)), "b2": _item("b2")}
    got = validate(_verdicts(("zz", Outcome.CLEAR, "x"), ("a1", Outcome.CONFIRM, "x"),
                             ("b2", Outcome.CLEAR, "x"), ("b2", Outcome.DEFER, "y")), residue)
    assert [(r.id, r.reason.split(":")[0].split(" ")[0]) for r in got] == [
        ("zz", "no"), ("a1", "outcome"), ("b2", "this"), ("b2", "this")]
    assert "no current lint finding" in got[0].reason
    assert "'confirm' is not allowed" in got[1].reason
    assert "more than once" in got[2].reason


def test_route_stores_each_accepted_verdict_with_its_provenance_and_rejects_the_rest(tmp_path: Path):
    ledger = JsonlLedger.at(tmp_path)
    receipt = route(_verdicts(("a1", Outcome.CONFIRM, "two jobs"), ("zz", Outcome.CLEAR, "x")),
                    {"a1": _item("a1")}, ledger, at="2026-01-01T00:00:00+00:00")
    assert (receipt.accepted, [r.id for r in receipt.rejected]) == (("a1",), ["zz"])
    [stored] = ledger.rulings()
    assert (stored.verdict.id, stored.verdict.outcome, stored.rule, stored.path) == ("a1", Outcome.CONFIRM, "class-cohesion", "m.py")
    assert (stored.fingerprint, stored.rubric_version, stored.at) == ("fp", "rv", "2026-01-01T00:00:00+00:00")
    assert ledger.latest("zz") is None


def test_route_stores_accepted_verdicts_in_document_order(tmp_path: Path):
    ledger = JsonlLedger.at(tmp_path)
    route(_verdicts(("b2", Outcome.CLEAR, "x"), ("a1", Outcome.DEFER, "x")), {"a1": _item("a1"), "b2": _item("b2")},
          ledger, at="t")
    assert [r.verdict.id for r in ledger.rulings()] == ["b2", "a1"]


def _analysis(root: Path, source: str = TWO_GROUPS) -> Analysis:
    (root / "m.py").write_text(source, encoding="utf-8")
    config = AnalysisConfig.defaults(RULE_REGISTRY)
    corpus = scan_corpus(root, config)
    return Analysis(root=root, report=Dispatcher(RULE_REGISTRY, config).run(corpus), corpus=corpus)


def _rule_on(root: Path, outcome: Outcome, source: str = TWO_GROUPS, reason: str = "because") -> Analysis:
    analysis = _analysis(root, source)
    [item] = FindingSource().residue(analysis)
    route(_verdicts((item.id, outcome, reason)), {item.id: item}, JsonlLedger.at(root), at="t")
    return analysis


def _status(settlement, subject: str) -> Status:
    [item] = [r for r in settlement.residue.values() if r.subject == subject]
    return item.status


def test_a_finding_never_ruled_on_is_a_warning_with_status_none(tmp_path: Path):
    analysis = _analysis(tmp_path)
    settlement = settle(analysis, JsonlLedger.at(tmp_path))
    assert settlement.report.warnings == analysis.report.warnings                  # no ledger: nothing moves
    assert _status(settlement, "m.A") is Status.NONE
    [position] = settlement.residue
    assert position == analysis.report.warnings[0].position                        # keyed by the finding it belongs to


def test_a_ruling_on_code_that_has_since_changed_is_stale_and_the_warning_returns(tmp_path: Path):
    _rule_on(tmp_path, Outcome.CLEAR)
    edited = settle(_analysis(tmp_path, TWO_GROUPS.replace("self.b", "self.b + 1")), JsonlLedger.at(tmp_path))
    assert [w.rule for w in edited.report.warnings] == ["class-cohesion"]
    assert _status(edited, "m.A") is Status.STALE


def test_a_finding_with_no_rubric_carries_no_residue(tmp_path: Path):
    branchy = "def f(v):\n" + "".join(f"    if v == {i}:\n        return {i}\n" for i in range(12)) + "    return 0\n"
    settlement = settle(_analysis(tmp_path, branchy), JsonlLedger.at(tmp_path))
    assert settlement.report.violations and settlement.residue == {}


def test_a_cleared_warning_disappears_and_the_run_stays_clean(tmp_path: Path):
    analysis = _rule_on(tmp_path, Outcome.CLEAR)
    settlement = settle(analysis, JsonlLedger.at(tmp_path))
    assert settlement.report.warnings == [] and settlement.report.violations == []
    assert settlement.report.exit_code() == 0 and settlement.residue == {}      # cleared: no status to show


def test_a_confirmed_warning_becomes_a_violation_that_carries_the_reason_and_fails_the_run(tmp_path: Path):
    analysis = _rule_on(tmp_path, Outcome.CONFIRM, reason="two unrelated jobs")
    settlement = settle(analysis, JsonlLedger.at(tmp_path))
    [violation] = settlement.report.violations
    assert violation.rule == "class-cohesion" and violation.message.endswith("[confirmed: two unrelated jobs]")
    assert settlement.report.warnings == [] and settlement.report.exit_code() == 1
    assert settlement.residue[violation.position].status is Status.CONFIRM      # can be ruled on again


def test_a_deferred_warning_and_a_stale_ruling_stay_warnings(tmp_path: Path):
    deferred = settle(_rule_on(tmp_path, Outcome.DEFER), JsonlLedger.at(tmp_path))
    assert [w.rule for w in deferred.report.warnings] == ["class-cohesion"] and deferred.report.violations == []
    assert _status(deferred, "m.A") is Status.DEFER


def test_settling_leaves_objective_findings_alone_and_in_order(tmp_path: Path):
    branchy = "def f(v):\n" + "".join(f"    if v == {i}:\n        return {i}\n" for i in range(12)) + "    return 0\n"
    mixed = _rule_on(tmp_path, Outcome.CLEAR, TWO_GROUPS + "\n\n" + branchy)
    settled = settle(mixed, JsonlLedger.at(tmp_path)).report
    assert "cyclomatic-complexity" in {v.rule for v in settled.violations}          # objective findings untouched
    assert [v.position for v in settled.violations] == sorted(v.position for v in settled.violations)


def test_a_confirmed_violation_is_placed_by_position_among_the_others(tmp_path: Path):
    # The class (line 1) is confirmed; the branchy function below it is an objective violation.
    branchy = "def f(v):\n" + "".join(f"    if v == {i}:\n        return {i}\n" for i in range(12)) + "    return 0\n"
    settled = settle(_rule_on(tmp_path, Outcome.CONFIRM, TWO_GROUPS + "\n\n" + branchy), JsonlLedger.at(tmp_path)).report
    assert [v.rule for v in settled.violations][:2] == ["class-cohesion", "cyclomatic-complexity"]


@pytest.mark.parametrize("outcome", [Outcome.CLEAR, Outcome.CONFIRM])
def test_a_ruling_applies_only_to_its_own_finding(tmp_path: Path, outcome: Outcome):
    two = TWO_GROUPS + "\n\n" + TWO_GROUPS.replace("class A", "class B")
    analysis = _analysis(tmp_path, two)
    first, second = FindingSource().residue(analysis)
    route(_verdicts((first.id, outcome, "r")), {first.id: first}, JsonlLedger.at(tmp_path), at="t")
    settled = settle(analysis, JsonlLedger.at(tmp_path)).report
    remaining = {w.subject for w in settled.warnings}
    assert second.subject in remaining and first.subject not in remaining


def test_editing_the_rubric_makes_earlier_rulings_stale(tmp_path: Path, monkeypatch):
    from slop.infer.bundle import prose
    import shutil
    bundle = tmp_path / "bundle"
    shutil.copytree(prose.ROOT / "references", bundle / "references")
    rubric = bundle / "references" / "rubrics" / "class-cohesion.md"
    monkeypatch.setattr(prose, "ROOT", bundle)
    project = tmp_path / "project"
    project.mkdir()
    _rule_on(project, Outcome.CLEAR)
    assert settle(_analysis(project), JsonlLedger.at(project)).report.warnings == []        # cleared
    rubric.write_text(rubric.read_text(encoding="utf-8") + "\nA new clause.\n", encoding="utf-8")
    edited = settle(_analysis(project), JsonlLedger.at(project))
    assert [w.rule for w in edited.report.warnings] == ["class-cohesion"]
    assert _status(edited, "m.A") is Status.STALE
