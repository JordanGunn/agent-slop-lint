"""The project's vocabulary: SKOS terms, read strictly, checked for integrity."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from slop import ontology
from slop.ontology import OntologyError, Scheme, Term

LAZ = Term("Laz", "The compressed LAS format: sequential chunk tables.", alt_labels=("Laszip",))
COPC = Term("Copc", "A cloud optimised point cloud: a Laz variant with VLRs and EVLRs.", broader=("Laz",))
INGRESS = Term("Ingress", "Data entering a system's boundary from outside.", hidden_labels=("Inbound",))
DRAFT = Term("Tile")


def _scheme(*terms: Term) -> Scheme:
    return Scheme("laszy", terms)


def test_a_word_finds_its_term_by_any_label_whatever_its_case():
    scheme = _scheme(LAZ, COPC, INGRESS)
    assert scheme.term("laszip") is LAZ and scheme.term("COPC") is COPC and scheme.term("inbound") is INGRESS
    assert scheme.term("Octree") is None


def test_the_preferred_word_replaces_alternative_and_retired_words_of_defined_terms_only():
    scheme = _scheme(LAZ, INGRESS, Term("Tile", alt_labels=("Chunk",)))
    assert (scheme.preferred("laszip"), scheme.preferred("Inbound")) == ("Laz", "Ingress")
    assert scheme.preferred("Laz") is None                     # already the preferred word
    assert scheme.preferred("chunk") is None                   # Tile has no definition yet: it binds nothing
    assert scheme.preferred("unknown") is None


def test_an_inflection_names_the_same_term_and_replaces_only_where_the_word_does():
    scheme = _scheme(LAZ, Term("Tile", "One square of a grid.", alt_labels=("Chunk",)))
    assert scheme.term("tiles") is scheme.term("Tile")
    assert scheme.preferred("Tiles") is None                   # the preferred word, inflected
    assert scheme.preferred("chunks") == "Tile"                # an alternative word, inflected


def test_two_terms_cannot_share_a_word_through_its_inflection():
    assert any("already names Tile" in p for p in ontology.problems(_scheme(Term("Tile", "x"), Term("Tiles", "y"))))


def test_narrower_terms_are_those_that_name_it_broader():
    assert _scheme(LAZ, COPC).narrower("laz") == (COPC,)


def test_the_file_round_trips(tmp_path: Path):
    scheme = _scheme(LAZ, COPC, INGRESS, DRAFT)
    ontology.save(scheme, tmp_path / ".slop" / "ontology.json")
    loaded = ontology.load(tmp_path / ".slop" / "ontology.json")
    assert (loaded.name, loaded.terms) == ("laszy", scheme.terms)


@pytest.mark.parametrize("document, message", [
    ({"version": 2, "scheme": "s", "terms": []}, "version"),
    ({"version": 1, "scheme": "s"}, "exactly the keys"),
    ({"version": 1, "scheme": "s", "terms": [{"definition": "x"}]}, "prefLabel"),
    ({"version": 1, "scheme": "s", "terms": [{"prefLabel": "A", "altlabel": ["b"]}]}, "unknown key"),
    ({"version": 1, "scheme": "s", "terms": [{"prefLabel": "A", "broader": "B"}]}, "broader must be a list"),
])
def test_a_malformed_file_is_an_error_that_names_the_problem(document, message):
    with pytest.raises(OntologyError, match=message):
        ontology.parse(document)


def test_a_missing_or_unreadable_file_is_an_error(tmp_path: Path):
    with pytest.raises(OntologyError, match="ontology draft"):
        ontology.load(tmp_path / "missing.json")
    (tmp_path / "bad.json").write_text("{", encoding="utf-8")
    with pytest.raises(OntologyError, match="cannot read"):
        ontology.load(tmp_path / "bad.json")


def test_a_consistent_scheme_has_no_problems():
    assert ontology.problems(_scheme(LAZ, COPC, INGRESS, DRAFT)) == ()


@pytest.mark.parametrize("terms, problem", [
    ((Term("Point Cloud", "x"),), "not a single word"),
    ((Term("Laz", "x", alt_labels=("laz",)),), "appears twice"),                       # SKOS S13
    ((LAZ, Term("Zip", "x", alt_labels=("Laszip",))), "already names Laz"),            # one word, one term
    ((Term("Copc", "x", broader=("Laz",)),), "names no term 'Laz'"),
    ((Term("A", "x", broader=("B",)), Term("B", "x", broader=("A",))), "leads back to itself"),
    ((LAZ, Term("Copc", "x", broader=("Laz",), related=("Laz",))), "also on its broader chain"),  # SKOS S27
])
def test_integrity_problems_are_named(terms, problem):
    assert any(problem in p for p in ontology.problems(_scheme(*terms)))


def test_check_command_reports_problems_and_exit_codes(tmp_path: Path, capsys):
    from slop import cli
    (tmp_path / "m.py").write_text("x = 1\n")
    (tmp_path / ".slop").mkdir()
    file = tmp_path / ".slop" / "ontology.json"
    file.write_text(json.dumps(ontology.dump(_scheme(LAZ, COPC))))
    assert cli.main(["ontology", "check", "--root", str(tmp_path)]) == 0
    file.write_text(json.dumps(ontology.dump(_scheme(LAZ, Term("Zip", "x", alt_labels=("laz",))))))
    assert cli.main(["ontology", "check", "--root", str(tmp_path)]) == 1
    assert "already names Laz" in capsys.readouterr().out
    file.write_text("{")
    assert cli.main(["ontology", "check", "--root", str(tmp_path)]) == 2


def test_show_prints_a_word_with_its_links(tmp_path: Path, capsys):
    from slop import cli
    (tmp_path / ".slop").mkdir()
    (tmp_path / ".slop" / "ontology.json").write_text(json.dumps(ontology.dump(_scheme(LAZ, COPC))))
    capsys.readouterr()
    assert cli.main(["ontology", "show", "laszip", "--root", str(tmp_path), "--output", "json"]) == 0
    shown = json.loads(capsys.readouterr().out)
    assert (shown["term"]["prefLabel"], shown["narrower"]) == ("Laz", ["Copc"])
