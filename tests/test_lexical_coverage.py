"""slop.lexical — observed vocabulary against a canonical one.

The canonical side is the real Open Ontology IR for ``support-desk`` (see
``test_ontology``), so the words asserted here are the ones the tool actually extracts.
The observed side is a hand-built :class:`~slop.lexicon.Lexicon` and, for the declared
names, a carved project.
"""
from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

import pytest

from slop import cli
from slop.lexical import canonical_tokens, coverage
from slop.lexicon import Lexicon, Role
from slop.ontology import OntologyIR, Term, TermKind, Vocabulary
from slop.scope import scan_corpus
from slop.scope.lexicon import build_declared_lexicon
from slop.span import Span

FIXTURE = Path(__file__).parent / "fixtures" / "support_desk.ir.json"


def _lexicon(*units: tuple[str, str]) -> Lexicon:
    """A Lexicon from ``(identifier, file)`` pairs."""
    return Lexicon([(text, Role.CALLABLE, Span(path, 0, 1)) for text, path in units])


class _Words(Vocabulary):
    """A vocabulary that does not come from Open Ontology: proves the seam."""

    def __init__(self, *names: str) -> None:
        self._terms = tuple(Term(n, TermKind.ENTITY, None, ()) for n in names)

    @property
    def name(self) -> str:
        return "words"

    def terms(self) -> Sequence[Term]:
        return self._terms


# ---- the canonical side ---------------------------------------------------

def test_canonical_tokens_are_the_words_of_names_and_field_keys():
    words = canonical_tokens(OntologyIR.load(FIXTURE))
    assert words["ticket"] == ("Ticket", "close-ticket", "escalate-ticket", "open-ticket")
    assert words["opened"] == ("Ticket",)            # from the field key ticket/opened-at
    assert words["escalated"] == ("escalated-to",)   # a different word from 'escalate'
    assert "escalate" in words and "tickets" in words  # no stemming: near misses stay apart


def test_descriptions_are_prose_and_are_not_tokenised():
    # Customer's description is "An organisation that raises tickets."
    assert "organisation" not in canonical_tokens(OntologyIR.load(FIXTURE))


# ---- coverage -------------------------------------------------------------

def test_coverage_splits_observed_tokens_into_defined_and_undefined():
    observed = _lexicon(("Ticket", "a.py"), ("triage_ticket", "a.py"), ("triage", "b.py"),
                        ("priority", "b.py"), ("sla_deadline", "b.py"))
    result = coverage(observed, OntologyIR.load(FIXTURE))
    assert [o.token for o in result.covered] == ["ticket", "priority"]   # most used first
    assert result.covered[0].count == 2 and result.covered[0].files == 1
    assert "Ticket" in result.covered[0].defined_by
    assert [(o.token, o.count, o.files) for o in result.undefined] == [
        ("triage", 2, 2), ("deadline", 1, 1), ("sla", 1, 1),
    ]
    assert result.occurrences_total == 7 and result.occurrences_covered == 3


def test_undefined_is_ordered_by_count_then_spread_then_name_and_is_never_filtered():
    observed = _lexicon(("alpha", "a.py"), ("alpha", "a.py"), ("beta", "a.py"), ("beta", "b.py"),
                        ("gamma", "a.py"), ("delta", "a.py"))
    undefined = [(o.token, o.count, o.files) for o in coverage(observed, _Words("zzz")).undefined]
    assert undefined == [("beta", 2, 2), ("alpha", 2, 1), ("delta", 1, 1), ("gamma", 1, 1)]


def test_a_canonical_word_the_code_never_uses_is_reported_unused():
    result = coverage(_lexicon(("ticket", "a.py")), OntologyIR.load(FIXTURE))
    assert "engineer" in result.unused and "ticket" not in result.unused


def test_a_canonical_word_the_noise_list_strips_is_unmeasurable_not_unused():
    # 'key' is in the Newman-14 noise list, so a Lexicon can never contain it. Calling it
    # "unused" would blame the code for something no measurement could see.
    result = coverage(_lexicon(("ticket", "a.py")), _Words("Key", "Ticket"))
    assert result.unmeasurable == ("key",)
    assert "key" not in result.unused


def test_coverage_refuses_a_vacuous_comparison():
    with pytest.raises(ValueError, match="vacuous"):
        coverage(Lexicon([]), OntologyIR.load(FIXTURE))
    with pytest.raises(ValueError, match="defines no words"):
        coverage(_lexicon(("ticket", "a.py")), _Words())


def test_coverage_is_deterministic():
    observed = _lexicon(("alpha", "a.py"), ("beta", "b.py"), ("ticket", "a.py"))
    vocabulary = OntologyIR.load(FIXTURE)
    assert coverage(observed, vocabulary) == coverage(observed, vocabulary)


# ---- the kernel's spread --------------------------------------------------

def test_spread_counts_distinct_files_and_ignores_fileless_units():
    lex = Lexicon([("alpha", Role.CALLABLE, Span("a.py", 0, 1)),
                   ("alpha", Role.CALLABLE, Span("a.py", 5, 6)),     # same file twice
                   ("alpha", Role.CALLABLE, Span("b.py", 0, 1)),
                   ("beta", Role.PACKAGE, Span("", 0, 0))])          # a fileless name
    assert lex.spread() == {"alpha": 2}
    assert lex.frequencies() == {"alpha": 3, "beta": 1}              # still counted


# ---- declared names -------------------------------------------------------

def test_declared_names_exclude_references_receivers_special_methods_and_unnamed(tmp_path: Path):
    (tmp_path / "shop.py").write_text(
        "import numpy as np\n\n"
        "class Ticket:\n"
        "    def __init__(self, title):\n"
        "        self.title = title\n\n"
        "    def close_ticket(self, reason):\n"
        "        return np.float64(reason)\n\n"
        "def triage(queue_depth):\n"
        "    return sorted(queue_depth, key=lambda q: q)\n"
    )
    corpus = scan_corpus(tmp_path, config=None)
    declared = set(build_declared_lexicon(corpus).frequencies())
    assert {"shop", "ticket", "title", "close", "reason", "triage", "queue", "depth"} <= declared
    assert not declared & {"self", "init", "np", "float", "numpy", "sorted", "lambda"}
    # The occurrence stream keeps the library and receiver noise; that is why it is not used.
    assert {"self", "np"} <= set(corpus.lexicon().frequencies())


def test_declared_names_carry_the_role_they_name(tmp_path: Path):
    (tmp_path / "m.py").write_text("class Ticket:\n    def close(self, reason):\n        pass\n")
    corpus = scan_corpus(tmp_path, config=None)
    lex = build_declared_lexicon(corpus)
    roles = {role for _text, role, _span in lex._units}
    assert {Role.MODULE, Role.CLASS, Role.CALLABLE, Role.PARAMETER} <= roles


# ---- the CLI --------------------------------------------------------------

def _project(root: Path) -> Path:
    (root / "shop.py").write_text(
        "class Ticket:\n    def close_ticket(self, reason):\n        return reason\n\n"
        "def triage(sla_deadline):\n    return sla_deadline\n"
    )
    return root


def test_lexicon_reports_coverage_against_an_ontology(tmp_path: Path, capsys):
    _project(tmp_path)
    assert cli.main(["lexicon", "--root", str(tmp_path), "--ontology", str(FIXTURE),
                     "--output", "json"]) == 0
    canonical = json.loads(capsys.readouterr().out)["canonical"]
    assert canonical["basis"] == "declared names"
    assert {"ticket", "close", "reason"} <= {o["token"] for o in canonical["covered"]}
    assert {"triage", "sla", "deadline"} <= {o["token"] for o in canonical["undefined"]}
    assert "engineer" in canonical["unused"] and "by" in canonical["unmeasurable"]


def test_lexicon_human_output_names_its_basis(tmp_path: Path, capsys):
    _project(tmp_path)
    assert cli.main(["lexicon", "--root", str(tmp_path), "--ontology", str(FIXTURE)]) == 0
    out = capsys.readouterr().out
    assert "over declared names" in out and "undefined (most used first" in out
    assert "triage(" in out


def test_lexicon_without_an_ontology_is_unchanged(tmp_path: Path, capsys):
    _project(tmp_path)
    cli.main(["lexicon", "--root", str(tmp_path), "--output", "json"])
    assert "canonical" not in json.loads(capsys.readouterr().out)


def test_lexicon_ontology_errors_are_exit_2(tmp_path: Path, capsys):
    _project(tmp_path)
    assert cli.main(["lexicon", "--root", str(tmp_path), "--ontology", "/nonexistent.json"]) == 2
    assert "cannot read ontology" in capsys.readouterr().err
