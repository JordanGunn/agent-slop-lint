"""The infer contract: schema and strict parsing come from one declaration."""
from __future__ import annotations

import copy
from dataclasses import dataclass

import pytest

from slop.infer.contract import (
    REASON_MAX_LENGTH, SCHEMA_VERSION, ContractError, Outcome, Receipt, Residue, Status, Verdicts, described, dump,
    parse, schema_of, schemas,
)

VERDICTS = {"version": "1", "verdicts": [
    {"id": "abc", "outcome": "clear", "reason": "A value object: its accessors share no field by design."},
    {"id": "def", "outcome": "confirm", "reason": "Two unrelated duties in one class."}]}

RESIDUE = {
    "id": "abc", "rule": "class-cohesion", "subject": "a.A", "locations": [{"path": "a.py", "first_line": 3, "last_line": 6}],
    "question": {"id": "cohesion.accessor-class", "text": "Is this a value object?", "outcomes": ["clear", "confirm", "defer"]},
    "rubric": {"command": "slop infer references rubrics/class-cohesion", "version": "9f"},
    "fingerprint": "00ff", "status": "none"}


@dataclass(frozen=True)
class _Measured:
    """A local declaration for the parts of the schema machinery no shipped document uses."""

    count: int = described("an int")
    value: float | None = described("an optional number")


def _with(doc: dict, path: list, value) -> dict:
    out = copy.deepcopy(doc)
    node = out
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value
    return out


def test_a_document_round_trips_through_parse_and_dump():
    assert dump(parse(Verdicts, VERDICTS)) == VERDICTS
    assert dump(parse(Residue, RESIDUE)) == RESIDUE


def test_unknown_missing_and_mistyped_fields_are_errors_that_name_the_path():
    with pytest.raises(ContractError, match=r"\$\.verdicts\[1\]: unknown field 'extra'"):
        parse(Verdicts, _with(VERDICTS, ["verdicts", 1, "extra"], 1))
    broken = copy.deepcopy(VERDICTS)
    del broken["verdicts"][0]["reason"]
    with pytest.raises(ContractError, match=r"\$\.verdicts\[0\]: missing field 'reason'"):
        parse(Verdicts, broken)
    with pytest.raises(ContractError, match=r"\$\.verdicts\[0\]\.id: expected str, got int"):
        parse(Verdicts, _with(VERDICTS, ["verdicts", 0, "id"], 7))
    with pytest.raises(ContractError, match=r"\$\.verdicts: expected an array, got dict"):
        parse(Verdicts, _with(VERDICTS, ["verdicts"], {}))
    with pytest.raises(ContractError, match=r"\$: expected an object, got list"):
        parse(Verdicts, [])


def test_the_outcome_vocabulary_is_closed():
    with pytest.raises(ContractError, match=r"'maybe' is not one of 'clear', 'confirm', 'defer'"):
        parse(Verdicts, _with(VERDICTS, ["verdicts", 0, "outcome"], "maybe"))


def test_reason_length_boundary_and_the_schema_agree():
    at_limit = _with(VERDICTS, ["verdicts", 0, "reason"], "x" * REASON_MAX_LENGTH)
    assert parse(Verdicts, at_limit).verdicts[0].reason == "x" * REASON_MAX_LENGTH
    with pytest.raises(ContractError, match="longer than 280"):
        parse(Verdicts, _with(VERDICTS, ["verdicts", 0, "reason"], "x" * (REASON_MAX_LENGTH + 1)))
    reason = schema_of(Verdicts)["properties"]["verdicts"]["items"]["properties"]["reason"]
    assert reason["maxLength"] == REASON_MAX_LENGTH            # the schema states what parse enforces


def test_an_empty_id_is_rejected():
    with pytest.raises(ContractError, match="shorter than 1"):
        parse(Verdicts, _with(VERDICTS, ["verdicts", 0, "id"], ""))


def test_a_document_of_another_version_is_rejected():
    with pytest.raises(ContractError, match=r"\$\.version: must be '1', got '2'"):
        parse(Verdicts, _with(VERDICTS, ["version"], "2"))


def test_numbers_and_booleans_are_not_confused():
    assert parse(_Measured, {"count": 1, "value": 3}).value == 3.0          # an int is a number
    assert parse(_Measured, {"count": 1, "value": None}).value is None      # optional
    with pytest.raises(ContractError, match="expected float, got bool"):
        parse(_Measured, {"count": 1, "value": True})
    with pytest.raises(ContractError, match="expected int, got bool"):
        parse(_Measured, {"count": True, "value": 1})


def test_the_status_vocabulary_is_closed():
    assert parse(Residue, RESIDUE).status is Status.NONE
    with pytest.raises(ContractError, match="'cleared' is not one of"):
        parse(Residue, _with(RESIDUE, ["status"], "cleared"))


def test_schemas_describe_every_document_closed_and_versioned():
    docs = schemas()
    assert set(docs) == {"residue", "verdicts", "receipt"}
    for name in ("verdicts", "receipt"):
        doc = docs[name]
        assert doc["additionalProperties"] is False, name
        assert doc["properties"]["version"]["const"] == SCHEMA_VERSION, name
        assert "version" in doc["required"], name
    outcome = docs["verdicts"]["properties"]["verdicts"]["items"]["properties"]["outcome"]
    assert outcome["enum"] == [o.value for o in Outcome]


def test_optional_fields_are_nullable_in_the_schema():
    value = schema_of(_Measured)["properties"]["value"]
    assert value["anyOf"] == [{"type": "number"}, {"type": "null"}]


def test_a_receipt_dumps_to_what_the_schema_describes():
    receipt = parse(Receipt, {"version": "1", "accepted": ["abc"],
                              "rejected": [{"id": "zzz", "reason": "not on the worklist"}], "ended": ["old"]})
    assert dump(receipt) == {"version": "1", "accepted": ["abc"],
                             "rejected": [{"id": "zzz", "reason": "not on the worklist"}], "ended": ["old"]}


def _fields_without_a_description(schema, path="$"):
    missing = []
    for name, prop in schema.get("properties", {}).items():
        here = f"{path}.{name}"
        if "description" not in prop:
            missing.append(here)
        for sub in (prop, prop.get("items", {}), *prop.get("anyOf", [])):
            missing += _fields_without_a_description(sub, here)
    return missing


def test_every_field_of_every_document_has_a_description_for_the_agent():
    for name, doc in schemas().items():
        assert _fields_without_a_description(doc, name) == []
