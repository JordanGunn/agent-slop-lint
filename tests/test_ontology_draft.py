"""Drafting the project's vocabulary from code, writing it as Open Ontology IR, checking it."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from slop import cli
from slop.ast import GRAMMARS_BY_ID
from slop.ontology.draft import draft
from slop.ontology.interface import TermKind
from slop.ontology.ir import OntologyError, OntologyIR
from slop.scope import scan_corpus

SOURCE = '''\
class Ticket:
    """A request from a customer. It has a title and a status.

    Later paragraphs are not part of the description.
    """

    def __init__(self, title, status):
        self.title = title
        self._status = status


class _Helper:
    """Private: not vocabulary."""


class Customer:
    def __init__(self, name):
        self.name = name
'''


def _draft(tmp_path: Path, files: dict[str, str]):
    for name, text in files.items():
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text(text, encoding="utf-8")
    return draft(scan_corpus(tmp_path, config=None), name="demo")


def test_each_public_class_is_an_entity_with_its_properties_and_first_sentence(tmp_path: Path):
    vocabulary = _draft(tmp_path, {"m.py": SOURCE})
    by_name = {t.name: t for t in vocabulary.terms()}
    assert set(by_name) == {"Ticket", "Customer"}                         # _Helper is private
    ticket = by_name["Ticket"]
    assert ticket.kind is TermKind.ENTITY
    assert ticket.fields == ("ticket/title", "ticket/status")              # leading underscore dropped
    assert ticket.description == "A request from a customer."              # first sentence only
    assert by_name["Customer"].description is None                         # no docstring: no guess
    assert vocabulary.name == "demo@0.1.0"


def test_a_name_defined_twice_is_drafted_once_from_the_first_file(tmp_path: Path):
    vocabulary = _draft(tmp_path, {"a.py": "class Chunk:\n    def __init__(self):\n        self.rows = 1\n",
                                   "b.py": "class Chunk:\n    def __init__(self):\n        self.cells = 1\n"})
    [chunk] = vocabulary.terms()
    assert chunk.fields == ("chunk/rows",)


def test_a_multiword_class_gets_a_kebab_namespace(tmp_path: Path):
    vocabulary = _draft(tmp_path, {"m.py": "class WorkOrder:\n    def __init__(self):\n        self.due = 1\n"})
    assert vocabulary.terms()[0].fields == ("work-order/due",)


def test_the_draft_round_trips_through_open_ontology_ir(tmp_path: Path):
    vocabulary = _draft(tmp_path, {"m.py": SOURCE})
    ir = vocabulary.as_ir()
    assert ir["kind"] == "ontology" and ir["name"] == "demo" and ir["version"] == "0.1.0"
    [ticket] = [o for o in ir["objectTypes"] if o["name"] == "Ticket"]
    assert ticket["kind"] == "object-type"
    assert ticket["properties"][0] == {"key": ":ticket/title", "name": "title", "valueType": {"kind": "json"},
                                       "required": False, "unique": False, "cardinality": "one"}
    assert OntologyIR.parse(ir).terms() == vocabulary.terms()


def test_the_shipped_example_ir_still_reads_and_round_trips():
    fixture = Path(__file__).parent / "fixtures" / "support_desk.ir.json"
    original = OntologyIR.load(fixture)
    assert OntologyIR.parse(original.as_ir()).terms() == original.terms()


@pytest.mark.parametrize("mutate, message", [
    (lambda ir: ir["objectTypes"][0].update(name="ticket"), "naming rule"),
    (lambda ir: ir["objectTypes"].append(dict(ir["objectTypes"][0])), "more than once"),
    (lambda ir: ir["objectTypes"][0]["properties"][0].update(key=":Ticket Title"), "namespace/name"),
])
def test_a_vocabulary_open_ontology_would_reject_is_rejected(tmp_path: Path, mutate, message):
    ir = _draft(tmp_path, {"m.py": SOURCE}).as_ir()
    mutate(ir)
    with pytest.raises(OntologyError, match=message):
        OntologyIR.parse(ir)


def test_only_python_reads_a_docstring():
    assert GRAMMARS_BY_ID["go"].docstring(None, b"") is None


def _run(capsys, *argv: str) -> tuple[int, str, str]:
    capsys.readouterr()
    code = cli.main(list(argv))
    out = capsys.readouterr()
    return code, out.out, out.err


def test_draft_writes_the_project_vocabulary_and_never_replaces_it_unasked(tmp_path: Path, capsys):
    (tmp_path / ".slop.toml").write_text("", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "m.py").write_text(SOURCE, encoding="utf-8")
    code, out, _ = _run(capsys, "ontology", "draft", "--root", str(tmp_path / "src"))
    target = tmp_path / ".slop" / "ontology.json"                          # the project root, not src/
    assert code == 0 and target.is_file() and "2 entities, 1 with a description" in out
    agreed = target.read_text(encoding="utf-8").replace("A request from a customer.", "Agreed meaning.")
    target.write_text(agreed, encoding="utf-8")
    code, _, err = _run(capsys, "ontology", "draft", "--root", str(tmp_path / "src"))
    assert code == 2 and "use --force" in err and target.read_text(encoding="utf-8") == agreed
    code, _, _ = _run(capsys, "ontology", "draft", "--root", str(tmp_path / "src"), "--force")
    assert code == 0 and "Agreed meaning." not in target.read_text(encoding="utf-8")


def test_check_accepts_a_valid_vocabulary_and_rejects_a_broken_edit(tmp_path: Path, capsys):
    (tmp_path / "m.py").write_text(SOURCE, encoding="utf-8")
    _run(capsys, "ontology", "draft", "--root", str(tmp_path))
    code, out, _ = _run(capsys, "ontology", "check", "--root", str(tmp_path))
    assert code == 0 and "valid: 2 terms" in out
    path = tmp_path / ".slop" / "ontology.json"
    ir = json.loads(path.read_text(encoding="utf-8"))
    ir["objectTypes"][0]["name"] = "not pascal"
    path.write_text(json.dumps(ir), encoding="utf-8")
    code, _, err = _run(capsys, "ontology", "check", "--root", str(tmp_path))
    assert code == 2 and "naming rule" in err


def test_vocab_uses_the_project_vocabulary_by_default_and_says_when_there_is_none(tmp_path: Path, capsys):
    (tmp_path / "m.py").write_text(SOURCE, encoding="utf-8")
    code, _, err = _run(capsys, "vocab", "--root", str(tmp_path))
    assert code == 2 and "slop ontology draft" in err
    _run(capsys, "ontology", "draft", "--root", str(tmp_path))
    code, out, _ = _run(capsys, "vocab", "--root", str(tmp_path), "--output", "json")
    assert code == 0 and {m["term"] for m in json.loads(out)["matched"]} == {"Ticket", "Customer"}
