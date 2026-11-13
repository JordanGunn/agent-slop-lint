"""The JSONL ledger: one ruling per id in a stable order, replaced whole, damage is loud."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from slop.infer.contract import Outcome, Ruling, Verdict
from slop.infer.ledger.interface import LedgerError
from slop.infer.ledger.jsonl import JsonlLedger


def _ruling(finding_id: str, outcome: Outcome = Outcome.CLEAR, *, reason: str = "r", at: str = "t1") -> Ruling:
    return Ruling(verdict=Verdict(id=finding_id, outcome=outcome, reason=reason), rule="class-cohesion",
                  path="a.py", fingerprint="fp", rubric_version="rv", at=at)


def test_the_ledger_of_a_project_lives_in_its_state_directory(tmp_path: Path):
    assert JsonlLedger.at(tmp_path).path == tmp_path / ".slop" / "inferences.jsonl"


def test_a_missing_file_is_an_empty_ledger(tmp_path: Path):
    assert list(JsonlLedger.at(tmp_path).rulings()) == []
    assert not (tmp_path / ".slop").exists()          # reading creates nothing


def test_rulings_round_trip_and_survive_a_new_instance(tmp_path: Path):
    first, second = _ruling("a", at="t1"), _ruling("b", Outcome.CONFIRM, reason="héllo", at="t2")
    JsonlLedger.at(tmp_path).write([second, first])
    assert list(JsonlLedger.at(tmp_path).rulings()) == [first, second]


def test_writing_replaces_the_record_in_path_then_id_order_one_line_each(tmp_path: Path):
    ledger = JsonlLedger.at(tmp_path)
    ledger.write([_ruling("a"), _ruling("z")])
    later = replace(_ruling("b"), path="0.py")
    ledger.write([_ruling("c"), later])
    assert [r.verdict.id for r in ledger.rulings()] == ["b", "c"]          # a and z are gone; 0.py sorts first
    assert len(ledger.path.read_text(encoding="utf-8").splitlines()) == 2


def test_an_empty_record_removes_the_file(tmp_path: Path):
    ledger = JsonlLedger.at(tmp_path)
    ledger.write([_ruling("a")])
    ledger.write([])
    assert not ledger.path.exists() and list(ledger.rulings()) == []


def test_a_damaged_line_is_an_error_that_names_the_file_and_line(tmp_path: Path):
    ledger = JsonlLedger.at(tmp_path)
    ledger.write([_ruling("a")])
    with ledger.path.open("a", encoding="utf-8") as out:
        out.write("{not json\n")
    with pytest.raises(LedgerError, match=r"inferences\.jsonl:2:"):
        list(ledger.rulings())


def test_a_line_that_breaks_the_contract_is_an_error_too(tmp_path: Path):
    ledger = JsonlLedger.at(tmp_path)
    ledger.path.parent.mkdir(parents=True)
    ledger.path.write_text('{"verdict": {"id": "a"}}\n', encoding="utf-8")
    with pytest.raises(LedgerError, match=r"inferences\.jsonl:1: .*missing field"):
        list(ledger.rulings())


def test_blank_lines_are_ignored(tmp_path: Path):
    ledger = JsonlLedger.at(tmp_path)
    ledger.write([_ruling("a")])
    with ledger.path.open("a", encoding="utf-8") as out:
        out.write("\n\n")
    assert len(list(ledger.rulings())) == 1
