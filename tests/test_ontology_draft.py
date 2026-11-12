"""Draft terms follow declared code words without overwriting editorial vocabulary."""
from __future__ import annotations

from pathlib import Path

from slop.lexicon import Lexicon, Role
from slop.ontology.check import problems
from slop.ontology.draft import draft
from slop.ontology.model import Scheme, Term
from slop.scope import scan_corpus
from slop.scope.lexicon import build_declared_lexicon
from slop.span import Span


def _lexicon(*units: tuple[str, str], stopwords: frozenset[str] | None = None) -> Lexicon:
    entries = [(word, Role.CALLABLE, Span(path, 0, 1)) for word, path in units]
    return Lexicon(entries) if stopwords is None else Lexicon(entries, stopwords=stopwords)


def test_draft_seeds_declared_words_by_frequency(tmp_path: Path):
    (tmp_path / "a.py").write_text(
        "class Parcel:\n    def route_parcel(self, request):\n        return request\n"
    )
    (tmp_path / "b.py").write_text("def route_parcel(parcel):\n    return parcel\n")
    lexicon = build_declared_lexicon(scan_corpus(tmp_path, config=None))

    scheme = draft(lexicon, None, "shipping")

    assert scheme.name == "shipping"
    assert [term.pref_label for term in scheme.terms] == ["parcel", "route", "request"]   # the realm's name (python) is slop's, not the project's
    assert all(not term.defined and term.definition is None for term in scheme.terms)
    assert not problems(scheme)


def test_draft_preserves_existing_terms_and_suppresses_every_existing_label():
    defined = Term("Parcel", "A unit in transit.", alt_labels=("Package",),
                   hidden_labels=("Pkg",), related=("Route",))
    route = Term("Route")
    existing = Scheme("canonical", (defined, route))
    lexicon = _lexicon(("package", "a.py"), ("PKG", "a.py"), ("parcel", "a.py"),
                       ("ROUTE", "a.py"), ("Depot", "a.py"))

    result = draft(lexicon, existing, "ignored")

    assert result.name == "canonical"
    assert result.terms == (defined, route, Term("Depot"))
    assert result.terms[0] is defined and result.terms[1] is route
    assert not problems(result)


def test_draft_excludes_stop_words_single_letters_and_numeric_tokens():
    lexicon = _lexicon(("the", "a.py"), ("ID", "a.py"), ("q", "a.py"),
                       ("123", "a.py"), ("Queue", "a.py"), stopwords=frozenset())

    result = draft(lexicon, None, "queues")

    assert result.terms == (Term("Queue"),)
    assert not problems(result)


def test_draft_orders_equal_frequencies_by_spread_then_word_and_uses_majority_casing():
    lexicon = _lexicon(("beta", "a.py"), ("beta", "b.py"),
                       ("ALPHA", "a.py"), ("alpha", "a.py"),
                       ("Gateway", "a.py"), ("Gateway", "b.py"),
                       ("gateway", "c.py"), ("delta", "b.py"), ("gamma", "a.py"))

    result = draft(lexicon, None, "names")

    assert [term.pref_label for term in result.terms] == ["Gateway", "beta", "ALPHA", "delta", "gamma"]
    assert draft(lexicon, None, "names").terms == result.terms
    assert not problems(result)
