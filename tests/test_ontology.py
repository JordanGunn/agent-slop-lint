"""slop.ontology — the vocabulary boundary, the Open Ontology IR reader, and the
observed-versus-canonical comparison.

``fixtures/support_desk.ir.json`` is the IR Open Ontology itself emits for its
``support-desk`` example (``pnpm model:check examples/support-desk/model.lisp --json``),
so the reader is tested against real output, not a hand-built imitation."""
from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

import pytest

from slop.ontology import (
    OntologyError, OntologyIR, Term, TermKind, Vocabulary, compare, normalize,
)
from slop.scope.find import Match
from slop.scope.identity import ScopeKind

FIXTURE = Path(__file__).parent / "fixtures" / "support_desk.ir.json"


def _match(name: str, path: str = "m.py") -> Match:
    return Match(ScopeKind.CLASS, name, f"m.{name}", path, 1)


# ---- normalize ------------------------------------------------------------

@pytest.mark.parametrize("a,b", [
    ("Chunk", "chunk"), ("Chunk", "CHUNK"),
    ("escalate-ticket", "escalate_ticket"), ("escalate-ticket", "EscalateTicket"),
    ("HTTPServer", "http_server"),
])
def test_normalize_treats_case_and_separators_as_the_same_word(a: str, b: str):
    assert normalize(a) == normalize(b)


@pytest.mark.parametrize("a,b", [("Store", "Stores"), ("Index", "OctreeIndex"), ("Key", "Keys")])
def test_normalize_does_not_fuzzy_match(a: str, b: str):
    assert normalize(a) != normalize(b)


# ---- OntologyIR (real IR) -------------------------------------------------

def test_load_reads_every_kind_of_term_from_real_ir():
    vocab = OntologyIR.load(FIXTURE)
    by_kind = {k: sorted(t.name for t in vocab.terms() if t.kind is k) for k in TermKind}
    assert by_kind[TermKind.ENTITY] == ["Customer", "Engineer", "Ticket"]
    assert by_kind[TermKind.RELATION] == ["escalated-to"]
    assert by_kind[TermKind.ACTION] == ["close-ticket", "escalate-ticket", "open-ticket"]
    assert by_kind[TermKind.QUERY] == ["escalations", "open-work", "tickets-by-status"]


def test_load_keeps_definition_fields_and_relation_ends():
    vocab = OntologyIR.load(FIXTURE)
    customer = vocab.term("Customer")
    assert customer.description == "An organisation that raises tickets."
    assert "ticket/title" in vocab.term("Ticket").fields          # leading ':' stripped
    assert vocab.term("escalated-to").ends == ("Ticket", "Engineer")
    assert vocab.term("escalate-ticket").fields == ("ticket", "engineer", "reason")
    assert vocab.name == "model@0.1.0"


def test_load_accepts_the_model_check_wrapper():
    ir = json.loads(FIXTURE.read_text())
    wrapped = OntologyIR.parse({"ok": True, "diagnostics": [], "ir": ir})
    assert [t.name for t in wrapped.entities()] == [t.name for t in OntologyIR.load(FIXTURE).entities()]


def test_term_matches_across_casing_and_prefers_an_entity():
    vocab = OntologyIR.load(FIXTURE)
    assert vocab.term("ticket").name == "Ticket"
    assert vocab.term("EscalatedTo").name == "escalated-to"
    assert vocab.term("Bogus") is None
    clash = OntologyIR("x", [
        Term("open-work", TermKind.QUERY, None, ()),
        Term("OpenWork", TermKind.ENTITY, None, ()),
    ])
    assert clash.term("open_work").kind is TermKind.ENTITY


@pytest.mark.parametrize("data,message", [
    ({"kind": "something-else"}, "not an Open Ontology IR"),
    ([], "not an Open Ontology IR"),
    ({"kind": "ontology", "objectTypes": "nope"}, "must be a list"),
    ({"kind": "ontology", "objectTypes": [{"properties": []}]}, "has no name"),
    ({"kind": "ontology", "objectTypes": [], "linkTypes": [{"name": "r", "from": "A", "to": "B"}]},
     "declares no entities"),
])
def test_parse_fails_loudly_instead_of_yielding_an_empty_vocabulary(data, message):
    with pytest.raises(OntologyError, match=message):
        OntologyIR.parse(data)


def test_load_reports_missing_and_malformed_files(tmp_path: Path):
    with pytest.raises(OntologyError, match="cannot read"):
        OntologyIR.load(tmp_path / "absent.json")
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    with pytest.raises(OntologyError, match="not valid JSON"):
        OntologyIR.load(bad)


# ---- compare --------------------------------------------------------------

def test_compare_splits_matched_unknown_and_unused():
    vocab = OntologyIR.load(FIXTURE)
    observed = [_match("Ticket"), _match("customer"), _match("Mystery")]
    result = compare(observed, vocab)
    assert [t.name for t, _ in result.matched] == ["Customer", "Ticket"]
    assert [m.name for m in result.unknown] == ["Mystery"]
    assert [t.name for t in result.unused] == ["Engineer"]


def test_compare_groups_every_class_that_agrees_with_one_term():
    vocab = OntologyIR.load(FIXTURE)
    twins = [_match("Ticket", "a.py"), _match("Ticket", "b.py")]
    ((term, matches),) = compare(twins, vocab).matched
    assert term.name == "Ticket"
    assert [m.path for m in matches] == ["a.py", "b.py"]     # a homonym stays visible


def test_compare_does_not_accept_a_near_miss():
    vocab = OntologyIR.load(FIXTURE)
    result = compare([_match("TicketManager"), _match("Tickets")], vocab)
    assert result.matched == ()
    assert len(result.unknown) == 2


def test_compare_refuses_a_vacuous_comparison():
    vocab = OntologyIR.load(FIXTURE)
    with pytest.raises(ValueError, match="vacuous"):
        compare([], vocab)


class _Fixed(Vocabulary):
    """A vocabulary that does not come from Open Ontology: proves the seam."""

    def __init__(self, *names: str) -> None:
        self._terms = tuple(Term(n, TermKind.ENTITY, None, ()) for n in names)

    @property
    def name(self) -> str:
        return "fixed"

    def terms(self) -> Sequence[Term]:
        return self._terms


def test_compare_works_over_any_vocabulary_implementation():
    result = compare([_match("Alpha"), _match("Beta")], _Fixed("alpha", "gamma"))
    assert [t.name for t, _ in result.matched] == ["alpha"]
    assert [m.name for m in result.unknown] == ["Beta"]
    assert [t.name for t in result.unused] == ["gamma"]


def test_compare_refuses_a_vocabulary_with_no_entities():
    with pytest.raises(ValueError, match="no entities"):
        compare([_match("Alpha")], _Fixed())
