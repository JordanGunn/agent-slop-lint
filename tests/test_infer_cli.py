"""`slop infer`: the schemas, the bundled prose, and the loop of lint, apply and lint again."""
from __future__ import annotations

import io
import json
import re
from pathlib import Path

import pytest

from slop import cli
from slop.infer.bundle import prose
from slop.infer.contract import Residue, parse

TWO_GROUPS = "class A:\n    def f(self):\n        return self.a\n\n    def g(self):\n        return self.b\n"


def _project(root: Path) -> None:
    (root / "m.py").write_text(TWO_GROUPS, encoding="utf-8")


def _run(capsys, *argv: str) -> tuple[int, str]:
    capsys.readouterr()
    code = cli.main(list(argv))
    return code, capsys.readouterr().out


def _residues(root: Path, capsys) -> list[dict]:
    """Each finding's residue from `slop lint --output json`, warnings and violations."""
    code, out = _run(capsys, "lint", "--root", str(root), "--output", "json")
    assert code in (0, 1)
    doc = json.loads(out)
    return [f["residue"] for f in doc["violations"] + doc["warnings"] if "residue" in f]


def _verdicts(root: Path, outcome: str, *, item_id: str, reason: str = "because") -> Path:
    path = root / "verdicts.json"
    path.write_text(json.dumps({"version": "1", "verdicts": [{"id": item_id, "outcome": outcome, "reason": reason}]}))
    return path


def test_schema_prints_every_document_or_one(capsys):
    code, out = _run(capsys, "infer", "schema")
    assert code == 0 and set(json.loads(out)) == {"residue", "verdicts", "receipt"}
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
    assert {"apply", "schema", "references"} <= named


def test_lint_json_carries_a_valid_residue_on_a_finding_that_needs_judgement(tmp_path: Path, capsys):
    _project(tmp_path)
    [raw] = _residues(tmp_path, capsys)
    item = parse(Residue, raw)
    assert (item.rule, item.subject, item.path, item.first_line, item.last_line) == ("class-cohesion", "m.A", "m.py", 1, 6)
    assert raw["status"] == "none"


def test_lint_json_attaches_no_residue_to_a_finding_without_a_rubric(tmp_path: Path, capsys):
    branchy = "def f(v):\n" + "".join(f"    if v == {i}:\n        return {i}\n" for i in range(12)) + "    return 0\n"
    (tmp_path / "m.py").write_text(branchy, encoding="utf-8")
    code, out = _run(capsys, "lint", "--root", str(tmp_path), "--output", "json")
    doc = json.loads(out)
    assert code == 1 and doc["violations"] and all("residue" not in f for f in doc["violations"])


def test_ruling_clear_removes_the_warning_and_its_residue(tmp_path: Path, capsys):
    _project(tmp_path)
    item_id = _residues(tmp_path, capsys)[0]["id"]
    code, out = _run(capsys, "infer", "apply", str(_verdicts(tmp_path, "clear", item_id=item_id)), "--root", str(tmp_path))
    assert code == 0 and json.loads(out)["accepted"] == [item_id]
    assert (tmp_path / ".slop" / "inferences.jsonl").is_file()
    code, out = _run(capsys, "lint", "--root", str(tmp_path), "--output", "json")
    assert code == 0 and json.loads(out)["warnings"] == []
    assert _residues(tmp_path, capsys) == []


def test_ruling_confirm_makes_the_lint_fail_says_why_and_can_be_ruled_again(tmp_path: Path, capsys):
    _project(tmp_path)
    item_id = _residues(tmp_path, capsys)[0]["id"]
    _run(capsys, "infer", "apply", str(_verdicts(tmp_path, "confirm", item_id=item_id, reason="two jobs")),
         "--root", str(tmp_path))
    code, out = _run(capsys, "lint", "--root", str(tmp_path))
    assert code == 1 and "[confirmed: two jobs]" in out
    [confirmed] = _residues(tmp_path, capsys)
    assert confirmed["status"] == "confirm"
    code, _ = _run(capsys, "infer", "apply", str(_verdicts(tmp_path, "clear", item_id=item_id)), "--root", str(tmp_path))
    assert code == 0 and _residues(tmp_path, capsys) == []                    # the newer ruling wins


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
    item_id = _residues(tmp_path, capsys)[0]["id"]
    document = _verdicts(tmp_path, "clear", item_id=item_id).read_text()
    monkeypatch.setattr("sys.stdin", io.StringIO(document))
    code, out = _run(capsys, "infer", "apply", "--root", str(tmp_path))
    assert code == 0 and json.loads(out)["accepted"] == [item_id]
