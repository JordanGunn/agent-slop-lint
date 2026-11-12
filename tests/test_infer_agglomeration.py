"""Agglomerations put to inference: a residue per group, rulings recorded but never failing a run."""
from __future__ import annotations

import json
from pathlib import Path

from slop import cli
from slop.infer.frame.rubric import rubric_for

_TANGLED = "    if a == {i}:\n        b {op}= {i}\n"


def _tangled(name: str, op: str = "+", extra: str = "") -> str:
    return f"def {name}(a, b):\n{extra}" + "".join(_TANGLED.format(i=i, op=op) for i in range(1, 25)) + "    return b\n"


def _project(tmp_path: Path) -> Path:
    """g names f across packages, and both are over the complexity limits: one cross-component group."""
    for name, text in {"b/__init__.py": "", "b/m.py": _tangled("f"), "a/__init__.py": "",
                       "a/n.py": "from b.m import f\n\n" + _tangled("g", "-", "    f(a, b)\n"),
                       ".slop.toml": "# project root\n"}.items():
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text(text, encoding="utf-8")
    return tmp_path


def _lint(capsys, root: Path) -> tuple[int, dict]:
    capsys.readouterr()
    code = cli.main(["lint", "--root", str(root), "--output", "json"])
    return code, json.loads(capsys.readouterr().out)


def _cross(doc: dict) -> dict:
    [group] = [g for g in doc["agglomerations"] if g["topology"] == "cross-component"]
    return group


def _rule(capsys, root: Path, group_id: str, outcome: str) -> int:
    verdicts = root / "verdicts.json"
    verdicts.write_text(json.dumps({"version": "1", "verdicts": [
        {"id": group_id, "outcome": outcome, "reason": "Both functions repeat one ladder that one table would replace."}]}))
    capsys.readouterr()
    code = cli.main(["infer", "apply", str(verdicts), "--root", str(root)])
    capsys.readouterr()
    return code


def test_the_question_is_closed_and_has_a_rubric():
    question, rubric = rubric_for("agglomeration")
    assert question.id == "agglomeration" and question.text.endswith("?")
    assert rubric.command == "slop infer references rubrics/agglomeration"


def test_a_group_carries_a_residue_that_reads_the_lead_first_and_every_member(tmp_path: Path, capsys):
    code, doc = _lint(capsys, _project(tmp_path))
    group = _cross(doc)
    residue = group["residue"]
    assert (residue["id"], residue["rule"], residue["subject"], residue["status"]) == (group["id"], "agglomeration", "m.f", "none")
    assert [loc["path"] for loc in residue["locations"]] == ["b/m.py", "a/n.py"]        # the lead, then the other member
    assert all(loc["first_line"] < loc["last_line"] for loc in residue["locations"])


def test_clearing_a_group_removes_it_and_confirming_records_it_without_failing(tmp_path: Path, capsys):
    root = _project(tmp_path)
    code, doc = _lint(capsys, root)
    group_id = _cross(doc)["id"]
    assert _rule(capsys, root, group_id, "confirm") == 0
    confirmed_code, confirmed = _lint(capsys, root)
    assert _cross(confirmed)["residue"]["status"] == "confirm"
    assert confirmed_code == code and confirmed["summary"] == doc["summary"]          # a group never fails a run
    assert _rule(capsys, root, group_id, "clear") == 0
    _, cleared = _lint(capsys, root)
    assert not [g for g in cleared["agglomerations"] if g["id"] == group_id]
    assert _rule(capsys, root, group_id, "defer") == 0                                  # a cleared group can be ruled again


def test_a_ruling_goes_stale_when_a_member_changes(tmp_path: Path, capsys):
    root = _project(tmp_path)
    _, doc = _lint(capsys, root)
    group_id = _cross(doc)["id"]
    _rule(capsys, root, group_id, "confirm")
    (root / "a" / "n.py").write_text("from b.m import f\n\n" + _tangled("g", "*", "    f(a, b)\n"), encoding="utf-8")
    _, after = _lint(capsys, root)
    assert _cross(after)["id"] == group_id and _cross(after)["residue"]["status"] == "stale"
