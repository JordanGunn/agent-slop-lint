"""slop.lexical — observed vocabulary against a canonical one.

The canonical side is a support-desk vocabulary of defined terms (with one draft term, which
defines nothing). The observed side is a hand-built :class:`~slop.lexicon.Lexicon` and, for
the declared names, a carved project.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from slop import cli
from slop.lexical import canonical_tokens, coverage
from slop.lexicon import Lexicon, Role
from slop import ontology
from slop.ontology import Scheme, Term
from slop.scope import scan_corpus
from slop.scope.find import walk
from slop.scope.lexicon import build_declared_lexicon, declared_units
from slop.span import Span

SUPPORT_DESK = Scheme("support-desk", [
    Term("Ticket", "A customer's request, tracked until it is closed.", alt_labels=("Case",)),
    Term("Customer", "An organisation that raises tickets."),
    Term("Engineer", "A person who works tickets."),
    Term("Close", "End a ticket's life, with a reason."),
    Term("Reason", "Why a ticket was closed."),
    Term("Priority", "How soon a ticket must be worked."),
    Term("By", "Who did something to a ticket."),
    Term("Triage"),                                  # a draft: no definition, so it defines nothing
])


def _file(root: Path) -> Path:
    path = root / "support_desk.json"
    path.write_text(json.dumps(ontology.dump(SUPPORT_DESK)), encoding="utf-8")
    return path


def _lexicon(*units: tuple[str, str]) -> Lexicon:
    """A Lexicon from ``(identifier, file)`` pairs."""
    return Lexicon([(text, Role.CALLABLE, Span(path, 0, 1)) for text, path in units])


def _words(*names: str) -> Scheme:
    return Scheme("words", [Term(n, f"the word {n}") for n in names])


# ---- the canonical side ---------------------------------------------------

def test_canonical_tokens_are_every_label_of_a_defined_term():
    words = canonical_tokens(SUPPORT_DESK)
    assert words["ticket"] == ("Ticket",) and words["case"] == ("Ticket",)   # an alternative label counts
    assert "triage" not in words                                            # a draft defines nothing


def test_definitions_are_prose_and_are_not_tokenised():
    assert "organisation" not in canonical_tokens(SUPPORT_DESK)


# ---- coverage -------------------------------------------------------------

def test_coverage_splits_observed_tokens_into_defined_and_undefined():
    observed = _lexicon(("Ticket", "a.py"), ("triage_ticket", "a.py"), ("triage", "b.py"),
                        ("priority", "b.py"), ("sla_deadline", "b.py"))
    result = coverage(observed, SUPPORT_DESK)
    assert [o.token for o in result.covered] == ["Ticket", "priority"]   # most used first, as the code spells it
    assert result.covered[0].count == 2 and result.covered[0].files == 1
    assert result.covered[0].defined_by == ("Ticket",)
    assert [(o.token, o.count, o.files) for o in result.undefined] == [
        ("triage", 2, 2), ("deadline", 1, 1), ("sla", 1, 1),
    ]
    assert result.occurrences_total == 7 and result.occurrences_covered == 3


def test_undefined_is_ordered_by_count_then_spread_then_name_and_is_never_filtered():
    observed = _lexicon(("alpha", "a.py"), ("alpha", "a.py"), ("beta", "a.py"), ("beta", "b.py"),
                        ("gamma", "a.py"), ("delta", "a.py"))
    undefined = [(o.token, o.count, o.files) for o in coverage(observed, _words("zzz")).undefined]
    assert undefined == [("beta", 2, 2), ("alpha", 2, 1), ("delta", 1, 1), ("gamma", 1, 1)]


def test_a_canonical_word_the_code_never_uses_is_reported_unused():
    result = coverage(_lexicon(("ticket", "a.py")), SUPPORT_DESK)
    assert "Engineer" in result.unused and "Ticket" not in result.unused


def test_a_canonical_word_the_noise_list_strips_is_unmeasurable_not_unused():
    # 'key' is in the Newman-14 noise list, so a Lexicon can never contain it. Calling it
    # "unused" would blame the code for something no measurement could see.
    result = coverage(_lexicon(("ticket", "a.py")), _words("Key", "Ticket"))
    assert result.unmeasurable == ("Key",)
    assert "Key" not in result.unused


def test_coverage_refuses_a_vacuous_comparison():
    with pytest.raises(ValueError, match="vacuous"):
        coverage(Lexicon([]), SUPPORT_DESK)
    with pytest.raises(ValueError, match="defines no words"):
        coverage(_lexicon(("ticket", "a.py")), _words())


def test_coverage_is_deterministic():
    observed = _lexicon(("alpha", "a.py"), ("beta", "b.py"), ("ticket", "a.py"))
    vocabulary = SUPPORT_DESK
    assert coverage(observed, vocabulary) == coverage(observed, vocabulary)


# ---- the lexicon's spread --------------------------------------------------

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
    assert set(corpus.lexicon().frequencies()) == declared          # a component's lexicon is its declared names


def test_declared_names_carry_the_role_they_name(tmp_path: Path):
    (tmp_path / "m.py").write_text("class Ticket:\n    def close(self, reason):\n        pass\n")
    corpus = scan_corpus(tmp_path, config=None)
    roles = {role for scope in walk(corpus) for _text, role, _span in declared_units(scope)}
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
    assert cli.main(["lexicon", "--root", str(tmp_path), "--ontology", str(_file(tmp_path)),
                     "--output", "json"]) == 0
    canonical = json.loads(capsys.readouterr().out)["canonical"]
    assert canonical["basis"] == "declared names"
    assert {"Ticket", "close", "reason"} <= {o["token"] for o in canonical["covered"]}
    assert {"triage", "sla", "deadline"} <= {o["token"] for o in canonical["undefined"]}
    assert "Engineer" in canonical["unused"] and "By" in canonical["unmeasurable"]


def test_lexicon_human_output_names_its_basis(tmp_path: Path, capsys):
    _project(tmp_path)
    assert cli.main(["lexicon", "--root", str(tmp_path), "--ontology", str(_file(tmp_path))]) == 0
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
    assert "no vocabulary at /nonexistent.json" in capsys.readouterr().err


def test_a_freshly_drafted_vocabulary_is_reported_as_covering_nothing_not_an_error(tmp_path: Path, capsys):
    _project(tmp_path)
    assert cli.main(["ontology", "draft", "--root", str(tmp_path)]) == 0
    capsys.readouterr()
    assert cli.main(["lexicon", "--root", str(tmp_path)]) == 0
    assert "no term has a definition yet" in capsys.readouterr().out
    assert cli.main(["lexicon", "--root", str(tmp_path), "--output", "json"]) == 0
    assert json.loads(capsys.readouterr().out)["canonical"]["defined"] == 0


def test_inflections_of_a_word_are_one_word_in_the_code_spelling_used_most():
    observed = _lexicon(("tickets", "a.py"), ("ticket_id", "a.py"), ("open_tickets", "b.py"), ("priorities", "b.py"))
    result = coverage(observed, SUPPORT_DESK)
    assert [(o.token, o.count, o.files) for o in result.covered] == [("tickets", 3, 2), ("priorities", 1, 1)]
    assert "Priority" not in result.unused
