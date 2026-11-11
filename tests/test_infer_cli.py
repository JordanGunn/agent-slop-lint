"""`slop infer schema` prints the schema of every document the exchange uses."""
from __future__ import annotations

import json

import pytest

from slop import cli


def test_schema_prints_one_json_object_with_every_document(capsys):
    assert cli.main(["infer", "schema"]) == 0
    docs = json.loads(capsys.readouterr().out)
    assert set(docs) == {"worklist", "verdicts", "receipt"}
    assert all(doc["type"] == "object" for doc in docs.values())


def test_infer_without_a_subcommand_is_a_usage_error():
    with pytest.raises(SystemExit) as exit_info:
        cli.main(["infer"])
    assert exit_info.value.code == 2
