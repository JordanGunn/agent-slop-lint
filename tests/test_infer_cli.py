"""`slop infer`: the schemas, the bundled prose, and the loop of next, apply and lint."""
from __future__ import annotations

import io
import json
import re
from pathlib import Path

import pytest

from slop import cli
from slop.infer.bundle import prose
from slop.infer.contract import Worklist, parse

TWO_GROUPS = "class A:\n    def f(self):\n        return self.a\n\n    def g(self):\n        return self.b\n"


def _project(root: Path) -> None:
    (root / "m.py").write_text(TWO_GROUPS, encoding="utf-8")


def _run(capsys, *argv: str) -> tuple[int, str]:
    capsys.readouterr()
    code = cli.main(list(argv))
    return code, capsys.readouterr().out


def _worklist(root: Path, capsys, *extra: str) -> dict:
    code, out = _run(capsys, "infer", "next", "--root", str(root), *extra)
    assert code == 0
    return json.loads(out)


def _verdicts(root: Path, outcome: str, *, item_id: str, reason: str = "because") -> Path:
    path = root / "verdicts.json"
    path.write_text(json.dumps({"version": "1", "verdicts": [{"id": item_id, "outcome": outcome, "reason": reason}]}))
    return path


def test_schema_prints_every_document_or_one(capsys):
    code, out = _run(capsys, "infer", "schema")
    assert code == 0 and set(json.loads(out)) == {"worklist", "verdicts", "receipt"}
    code, out = _run(capsys, "infer", "schema", "verdicts")
    assert code == 0 and json.loads(out)["title"] == "Verdicts"
    with pytest.raises(SystemExit) as exit_info:
        cli.main(["infer", "schema", "nonsense"])
    assert exit_info.value.code == 2


def test_infer_without_a_subcommand_is_a_usage_error():
    with pytest.raises(SystemExit) as exit_info:
        cli.main(["infer"])
    assert exit_info.value.code == 2


def test_instructions_and_references_are_printed_from_the_bundle(capsys):
    code, out = _run(capsys, "infer", "instructions")
    assert code == 0 and out == prose.instructions()
    code, out = _run(capsys, "infer", "references")
    assert code == 0 and "rubrics/class-cohesion" in out.splitlines()
    code, out = _run(capsys, "infer", "references", "rubrics/class-cohesion")
    assert code == 0 and out == prose.reference("rubrics/class-cohesion")


def test_an_unknown_reference_is_an_error(capsys):
    capsys.readouterr()
    assert cli.main(["infer", "references", "../../etc/passwd"]) == 2
    assert "no reference" in capsys.readouterr().err


def test_the_instructions_name_only_real_commands_and_every_command(capsys):
    named = set(re.findall(r"slop infer (\w+)", prose.instructions()))
    for command in named:
        with pytest.raises(SystemExit) as exit_info:
            cli.main(["infer", command, "--help"])
        assert exit_info.value.code == 0, command           # `--help` on a real command exits 0
    assert {"next", "apply", "schema", "references"} <= named


def test_next_prints_a_valid_worklist_with_the_finding_to_judge(tmp_path: Path, capsys):
    _project(tmp_path)
    doc = _worklist(tmp_path, capsys)
    [item] = parse(Worklist, doc).items
    assert (item.rule, item.subject, item.path) == ("class-cohesion", "m.A", "m.py")


def test_ruling_clear_removes_the_warning_and_the_finding_leaves_the_worklist(tmp_path: Path, capsys):
    _project(tmp_path)
    item_id = _worklist(tmp_path, capsys)["items"][0]["id"]
    code, out = _run(capsys, "infer", "apply", str(_verdicts(tmp_path, "clear", item_id=item_id)), "--root", str(tmp_path))
    assert code == 0 and json.loads(out)["accepted"] == [item_id]
    assert (tmp_path / ".slop" / "inferences.jsonl").is_file()
    code, out = _run(capsys, "lint", "--root", str(tmp_path), "--output", "json")
    assert code == 0 and json.loads(out)["warnings"] == []
    assert _worklist(tmp_path, capsys)["items"] == []


def test_ruling_confirm_makes_the_lint_fail_and_says_why(tmp_path: Path, capsys):
    _project(tmp_path)
    item_id = _worklist(tmp_path, capsys)["items"][0]["id"]
    _run(capsys, "infer", "apply", str(_verdicts(tmp_path, "confirm", item_id=item_id, reason="two jobs")),
         "--root", str(tmp_path))
    code, out = _run(capsys, "lint", "--root", str(tmp_path))
    assert code == 1 and "[confirmed: two jobs]" in out


def test_a_verdict_for_an_unknown_finding_is_rejected_stores_nothing_and_exits_one(tmp_path: Path, capsys):
    _project(tmp_path)
    code, out = _run(capsys, "infer", "apply", str(_verdicts(tmp_path, "clear", item_id="nope")), "--root", str(tmp_path))
    receipt = json.loads(out)
    assert code == 1 and receipt["accepted"] == [] and receipt["rejected"][0]["id"] == "nope"
    assert not (tmp_path / ".slop").exists()


def test_a_document_that_is_not_valid_is_exit_two(tmp_path: Path, capsys):
    _project(tmp_path)
    bad = tmp_path / "bad.json"
    bad.write_text('{"version": "1", "verdicts": [{"id": "x", "outcome": "maybe", "reason": "r"}]}')
    capsys.readouterr()
    assert cli.main(["infer", "apply", str(bad), "--root", str(tmp_path)]) == 2
    assert "'maybe' is not one of" in capsys.readouterr().err
    bad.write_text("{not json")
    assert cli.main(["infer", "apply", str(bad), "--root", str(tmp_path)]) == 2


def test_apply_reads_stdin_by_default(tmp_path: Path, capsys, monkeypatch):
    _project(tmp_path)
    item_id = _worklist(tmp_path, capsys)["items"][0]["id"]
    document = _verdicts(tmp_path, "clear", item_id=item_id).read_text()
    monkeypatch.setattr("sys.stdin", io.StringIO(document))
    code, out = _run(capsys, "infer", "apply", "--root", str(tmp_path))
    assert code == 0 and json.loads(out)["accepted"] == [item_id]


def test_next_can_be_limited_and_refuses_a_rule_that_has_no_rubric(tmp_path: Path, capsys):
    (tmp_path / "m.py").write_text(TWO_GROUPS + "\n\n" + TWO_GROUPS.replace("class A", "class B"), encoding="utf-8")
    assert len(_worklist(tmp_path, capsys)["items"]) == 2
    assert len(_worklist(tmp_path, capsys, "--limit", "1")["items"]) == 1
    capsys.readouterr()
    assert cli.main(["infer", "next", "--root", str(tmp_path), "--rule", "cyclomatic-complexity"]) == 2
    assert "has no rubric" in capsys.readouterr().err
