"""The preferred-term rule applies only the project's defined vocabulary to declarations."""
from __future__ import annotations

import json

from slop import cli


_SOURCE = ("def get_user(get_count):\n"
           "    return get_count\n\n"
           "def read_file():\n"
           "    return None\n\n"
           "def fetch_user():\n"
           "    return None\n")


def _source(tmp_path):
    (tmp_path / "names.py").write_text(_SOURCE)


def _vocabulary(tmp_path):
    state = tmp_path / ".slop"
    state.mkdir()
    (state / "ontology.json").write_text(json.dumps({
        "version": 1,
        "scheme": "example",
        "terms": [
            {"prefLabel": "Fetch", "definition": "Retrieve a resource.", "altLabel": ["get"]},
            {"prefLabel": "Load", "altLabel": ["read"]},
        ],
    }))


def test_lint_reports_defined_alternatives_once_at_each_declaration(tmp_path, capsys):
    _source(tmp_path)
    _vocabulary(tmp_path)

    assert cli.main(["lint", "--root", str(tmp_path), "--output", "json"]) == 1
    doc = json.loads(capsys.readouterr().out)
    findings = [v for v in doc["violations"] if v["rule"] == "preferred-term"]
    assert len(findings) == 2
    assert len({v["id"] for v in findings}) == 2
    assert {v["message"] for v in findings} == {
        "name 'get_user' uses 'get'; the vocabulary's word is 'Fetch'",
        "name 'get_count' uses 'get'; the vocabulary's word is 'Fetch'",
    }
    assert {v["subject"] for v in findings} == {"names.get_user"}
    assert all(v["value"] == 1 and v["threshold"] == 0 for v in findings)


def test_lint_without_vocabulary_has_no_preferred_term_findings(tmp_path, capsys):
    _source(tmp_path)

    cli.main(["lint", "--root", str(tmp_path), "--output", "json"])
    doc = json.loads(capsys.readouterr().out)
    assert not [v for v in doc["violations"] if v["rule"] == "preferred-term"]


def test_malformed_vocabulary_is_an_error_not_a_clean_run(tmp_path, capsys):
    _source(tmp_path)
    state = tmp_path / ".slop"
    state.mkdir()
    (state / "ontology.json").write_text("{invalid")

    assert cli.main(["lint", "--root", str(tmp_path), "--output", "json"]) == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert output.err.startswith("slop: error: ")
    assert "ontology.json" in output.err


def test_check_preferred_term_runs_the_rule(tmp_path, capsys):
    _source(tmp_path)
    _vocabulary(tmp_path)

    assert cli.main(["check", "preferred-term", "--root", str(tmp_path), "--output", "json"]) == 1
    doc = json.loads(capsys.readouterr().out)
    assert len(doc["violations"]) == 2
    assert {v["rule"] for v in doc["violations"]} == {"preferred-term"}


def test_a_package_named_with_a_replaced_word_is_reported_once(tmp_path, capsys):
    (tmp_path / "get_tools").mkdir()
    (tmp_path / "get_tools" / "__init__.py").write_text("")
    (tmp_path / "get_tools" / "m.py").write_text("x = 1\n")
    _vocabulary(tmp_path)
    cli.main(["lint", "--root", str(tmp_path), "--output", "json"])
    doc = json.loads(capsys.readouterr().out)
    names = [v["message"] for v in doc["violations"] if v["rule"] == "preferred-term"]
    assert names == ["name 'get_tools' uses 'get'; the vocabulary's word is 'Fetch'"]
