"""Rubrics bind a rule to one closed question and a versioned rubric; excerpts are bounded."""
from __future__ import annotations

from pathlib import Path

import pytest

from slop.infer.contract import Outcome
from slop.infer.bundle import prose
from slop.infer.frame import rubric
from slop.infer.frame.excerpt import MAX_LINES, excerpt


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


def _file(tmp_path: Path, n: int) -> Path:
    path = tmp_path / "pkg" / "m.py"
    path.parent.mkdir(exist_ok=True)
    path.write_text("".join(f"line {i}\n" for i in range(1, n + 1)), encoding="utf-8")
    return path


def test_an_excerpt_is_the_inclusive_line_range_labelled_relative_to_the_root(tmp_path: Path):
    got = excerpt(_file(tmp_path, 10), tmp_path, 3, 5)
    assert (got.path, got.first_line, got.last_line, got.text) == ("pkg/m.py", 3, 5, "line 3\nline 4\nline 5")


def test_an_excerpt_past_the_end_of_the_file_is_clipped(tmp_path: Path):
    got = excerpt(_file(tmp_path, 4), tmp_path, 3, 99)
    assert (got.last_line, got.text) == (4, "line 3\nline 4")


def test_a_long_span_is_cut_and_last_line_says_where(tmp_path: Path):
    got = excerpt(_file(tmp_path, MAX_LINES * 3), tmp_path, 10, 10 + MAX_LINES * 2)
    assert got.last_line == 10 + MAX_LINES - 1
    assert len(got.text.splitlines()) == MAX_LINES


def test_the_limit_is_exactly_max_lines(tmp_path: Path):
    path = _file(tmp_path, MAX_LINES + 5)
    assert excerpt(path, tmp_path, 1, MAX_LINES).last_line == MAX_LINES              # fits: not cut
    assert excerpt(path, tmp_path, 1, MAX_LINES + 1).last_line == MAX_LINES          # one over: cut


def test_a_path_outside_the_root_keeps_its_own_path(tmp_path: Path):
    other = tmp_path / "elsewhere"
    other.mkdir()
    path = other / "x.py"
    path.write_text("a\n", encoding="utf-8")
    root = tmp_path / "root"
    root.mkdir()
    assert excerpt(path, root, 1, 1).path == path.resolve().as_posix()
