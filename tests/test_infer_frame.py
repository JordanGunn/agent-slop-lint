"""Rubrics bind a rule to one closed question and a versioned rubric."""
from __future__ import annotations

from pathlib import Path

import pytest

from slop.infer.contract import Outcome
from slop.infer.bundle import prose
from slop.infer.frame import rubric
from slop.rules import RULE_REGISTRY


@pytest.fixture
def rubrics(tmp_path: Path, monkeypatch) -> Path:
    directory = tmp_path / "references" / "rubrics"
    directory.mkdir(parents=True)
    (directory / "class-cohesion.md").write_text("# draft\n\nQuestion: One job?\n", encoding="utf-8")
    monkeypatch.setattr(prose, "ROOT", tmp_path)
    return directory


def test_a_rule_with_a_rubric_has_a_closed_question_and_a_command_to_read_it(rubrics: Path):
    question, ref = rubric.rubric_for("class-cohesion")
    assert question.outcomes == (Outcome.CLEAR, Outcome.CONFIRM, Outcome.DEFER)
    assert question.id == "class-cohesion" and question.text == "One job?"
    assert ref.command == "slop infer references rubrics/class-cohesion"


def test_editing_a_rubric_changes_its_version_and_only_then(rubrics: Path):
    before = rubric.rubric_for("class-cohesion")[1].version
    assert rubric.rubric_for("class-cohesion")[1].version == before
    (rubrics / "class-cohesion.md").write_text("# draft\n\nQuestion: One job?\n\nmore\n", encoding="utf-8")
    assert rubric.rubric_for("class-cohesion")[1].version != before


def test_a_rule_without_a_rubric_cannot_be_put_to_inference(rubrics: Path):
    with pytest.raises(KeyError):
        rubric.rubric_for("cyclomatic-complexity")


def test_a_rubric_file_alone_makes_a_rule_inferable(rubrics: Path):
    (rubrics / "rigid-package.md").write_text("Question: Will it change?\n", encoding="utf-8")
    assert rubric.rubric_for("rigid-package")[0].text == "Will it change?"


def test_a_rubric_that_states_no_question_is_an_error(rubrics: Path):
    (rubrics / "class-cohesion.md").write_text("# draft\n", encoding="utf-8")
    with pytest.raises(ValueError):
        rubric.rubric_for("class-cohesion")


@pytest.mark.parametrize("rule", ["agglomeration", *(r.name for r in RULE_REGISTRY if r.subjective)])
def test_every_subjective_rule_ships_a_rubric_that_states_its_question(rule: str):
    question, ref = rubric.rubric_for(rule)
    assert question.text.endswith("?") and len(ref.version) == 12
