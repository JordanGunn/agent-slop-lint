"""Rubrics bind a rule to one closed question and a versioned rubric."""
from __future__ import annotations

from pathlib import Path

import pytest

from slop.infer.contract import Outcome
from slop.infer.bundle import prose
from slop.infer.frame import rubric


@pytest.fixture
def rubrics(tmp_path: Path, monkeypatch) -> Path:
    directory = tmp_path / "references" / "rubrics"
    directory.mkdir(parents=True)
    (directory / "class-cohesion.md").write_text("first draft", encoding="utf-8")
    monkeypatch.setattr(prose, "ROOT", tmp_path)
    return directory


def test_a_rule_with_a_rubric_has_a_closed_question_and_a_command_to_read_it(rubrics: Path):
    question, ref = rubric.rubric_for("class-cohesion")
    assert question.outcomes == (Outcome.CLEAR, Outcome.CONFIRM, Outcome.DEFER)
    assert question.id == "class-cohesion.responsibility" and question.text.endswith("?")
    assert ref.command == "slop infer references rubrics/class-cohesion"


def test_editing_a_rubric_changes_its_version_and_only_then(rubrics: Path):
    before = rubric.rubric_for("class-cohesion")[1].version
    assert rubric.rubric_for("class-cohesion")[1].version == before
    (rubrics / "class-cohesion.md").write_text("second draft", encoding="utf-8")
    assert rubric.rubric_for("class-cohesion")[1].version != before


def test_a_rule_without_a_rubric_cannot_be_put_to_inference(rubrics: Path):
    assert not rubric.has_rubric("cyclomatic-complexity")
    with pytest.raises(KeyError):
        rubric.rubric_for("cyclomatic-complexity")


def test_a_question_without_its_rubric_file_is_not_inferable(rubrics: Path):
    (rubrics / "class-cohesion.md").unlink()
    assert not rubric.has_rubric("class-cohesion")


def test_the_shipped_rubric_exists_and_is_hashable():
    assert rubric.has_rubric("class-cohesion")
    assert len(rubric.rubric_for("class-cohesion")[1].version) == 12
