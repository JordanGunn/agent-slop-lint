"""FindingSource turns subjective warnings of rubric-backed rules into residue."""
from __future__ import annotations

from pathlib import Path

from slop.config import AnalysisConfig
from slop.dispatch import Dispatcher
from slop.infer.contract import Outcome, Status
from slop.infer.source.finding import FindingSource
from slop.infer.source.interface import Analysis
from slop.rules import RULE_REGISTRY
from slop.scope import scan_corpus

TWO_GROUPS = "class A:\n    def f(self):\n        return self.a\n\n    def g(self):\n        return self.b\n"


def _analyse(root: Path) -> Analysis:
    config = AnalysisConfig.defaults(RULE_REGISTRY)
    corpus = scan_corpus(root, config)
    return Analysis(root=root, report=Dispatcher(RULE_REGISTRY, config).run(corpus), corpus=corpus)


def _residue(root: Path, source: str):
    (root / "m.py").write_text(source, encoding="utf-8")
    return list(FindingSource().residue(_analyse(root)))


def test_a_cohesion_warning_becomes_one_residue_spanning_the_whole_class(tmp_path: Path):
    [item] = _residue(tmp_path, TWO_GROUPS)
    assert (item.rule, item.subject) == ("class-cohesion", "m.A")
    assert [(loc.path, loc.first_line, loc.last_line) for loc in item.locations] == [("m.py", 1, 6)]
    assert item.question.outcomes == (Outcome.CLEAR, Outcome.CONFIRM, Outcome.DEFER)
    assert item.rubric.command == "slop infer references rubrics/class-cohesion"
    assert item.status is Status.NONE                       # the source does not know the ledger


def test_the_span_and_fingerprint_cover_the_definition_and_nothing_around_it(tmp_path: Path):
    [item] = _residue(tmp_path, "import os\n\n" + TWO_GROUPS + "\n\nafter = 1\n")
    assert (item.locations[0].first_line, item.locations[0].last_line) == (3, 8)
    [around] = _residue(tmp_path, "import sys\n\n" + TWO_GROUPS + "\n\nafter = 2\n")
    assert around.fingerprint == item.fingerprint           # code around the class changed: same ruling holds


def test_a_moved_class_keeps_its_id_and_fingerprint_but_an_edited_one_only_its_id(tmp_path: Path):
    [original] = _residue(tmp_path, TWO_GROUPS)
    [moved] = _residue(tmp_path, "import os\n\n\n" + TWO_GROUPS)
    assert (moved.id, moved.fingerprint) == (original.id, original.fingerprint) and moved.locations[0].first_line == 4
    [edited] = _residue(tmp_path, TWO_GROUPS.replace("self.b", "self.b + 1"))
    assert edited.id == original.id and edited.fingerprint != original.fingerprint


def test_a_subjective_rule_without_a_rubric_is_not_residue(tmp_path: Path):
    # `lib` is stable (three dependents) and concrete: rigid-package warns, and has no rubric.
    for package in ("lib", "a", "b", "c"):
        (tmp_path / package).mkdir()
        (tmp_path / package / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "lib" / "core.py").write_text("class C:\n    pass\n\ndef f():\n    return 1\n", encoding="utf-8")
    for package in ("a", "b", "c"):
        (tmp_path / package / "m.py").write_text("from lib import core\n\ndef g():\n    return core.f()\n", encoding="utf-8")
    analysis = _analyse(tmp_path)
    assert "rigid-package" in {w.rule for w in analysis.report.warnings}      # the fixture really warns
    assert list(FindingSource().residue(analysis)) == []


def test_an_objective_violation_is_never_residue(tmp_path: Path):
    branchy = "def f(v):\n" + "".join(f"    if v == {i}:\n        return {i}\n" for i in range(12)) + "    return 0\n"
    (tmp_path / "m.py").write_text(branchy, encoding="utf-8")
    analysis = _analyse(tmp_path)
    assert "cyclomatic-complexity" in {v.rule for v in analysis.report.violations}   # the fixture really violates
    assert list(FindingSource().residue(analysis)) == []


def test_two_findings_in_one_file_get_different_ids(tmp_path: Path):
    items = _residue(tmp_path, TWO_GROUPS + "\n\n" + TWO_GROUPS.replace("class A", "class B"))
    assert sorted(i.subject for i in items) == ["m.A", "m.B"] and len({i.id for i in items}) == 2
