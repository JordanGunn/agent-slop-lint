"""scope.find — discovery over the ownership tree: where a name is defined, what a scope
holds, which names are defined more than once. Facts only; order is deterministic."""
from __future__ import annotations

from pathlib import Path

from slop.scope import scan_corpus
from slop.scope.find import collisions, find, outline
from slop.scope.identity import ScopeKind


def _corpus(root: Path):
    return scan_corpus(root, config=None)


def test_find_reports_path_and_line_of_a_definition(sample_project: Path):
    (match,) = find(_corpus(sample_project), "Address")
    assert match.kind is ScopeKind.CLASS
    assert match.path == "store/address.py"
    assert match.line == 1


def test_find_line_counts_from_the_definition_not_the_file_top(sample_project: Path):
    # index/octree.py opens with a docstring and a blank line; the class is on line 3.
    octree = [m for m in find(_corpus(sample_project), "Index") if m.path == "index/octree.py"]
    assert [m.line for m in octree] == [3]


def test_find_matches_exact_name_only(sample_project: Path):
    corpus = _corpus(sample_project)
    assert find(corpus, "Stor") == []          # a prefix is not the name
    assert find(corpus, "STORE") == []         # case is significant
    assert len(find(corpus, "Store")) == 2


def test_find_kind_separates_a_function_from_a_class_of_the_same_word(sample_project: Path):
    (sample_project / "other.py").write_text("class Thing:\n    pass\n")
    corpus = _corpus(sample_project)
    assert [m.path for m in find(corpus, "Thing", kind=ScopeKind.CLASS)] == ["other.py"]
    assert [m.path for m in find(corpus, "Thing", kind=ScopeKind.CALLABLE)] == ["thing.py"]


def test_find_under_restricts_to_a_subtree(sample_project: Path):
    corpus = _corpus(sample_project)
    store = next(s for s in _walk(corpus) if s.id.kind is ScopeKind.PACKAGE and s.name == "store")
    assert {m.path for m in find(corpus, "Store", under=store)} == {"store/array.py", "store/frame.py"}
    assert find(corpus, "Index", under=store) == []   # defined elsewhere in the corpus


def test_find_is_deterministic(sample_project: Path):
    first = find(_corpus(sample_project), kind=ScopeKind.CLASS)
    second = find(_corpus(sample_project), kind=ScopeKind.CLASS)
    assert first == second
    assert first == sorted(first, key=lambda m: m.sort_key())


def test_collisions_lists_only_names_defined_more_than_once(sample_project: Path):
    groups = collisions(_corpus(sample_project))
    assert set(groups) == {"Index", "Store", "Twin"}
    assert "Address" not in groups


def test_collisions_keeps_same_qualname_definitions_apart_by_path(sample_project: Path):
    # a/mod.py and b/mod.py both carve to the qualname 'mod.Twin'.
    twins = collisions(_corpus(sample_project))["Twin"]
    assert {m.qualname for m in twins} == {"mod.Twin"}
    assert {m.path for m in twins} == {"a/mod.py", "b/mod.py"}


def test_collisions_default_kind_is_class_so_methods_do_not_flood(sample_project: Path):
    # Both Store classes define 'save'; that is a collision of callables, not classes.
    assert "save" not in collisions(_corpus(sample_project))
    assert "save" in collisions(_corpus(sample_project), kind=ScopeKind.CALLABLE)


def test_outline_levels_and_depth(sample_project: Path):
    corpus = _corpus(sample_project)
    full = outline(corpus, corpus.root)
    shallow = outline(corpus, corpus.root, depth=1)
    assert len(shallow) < len(full)
    assert min(level for level, _ in full) == 1
    assert max(level for level, _ in shallow) == 1


def test_outline_kinds_hides_other_kinds_but_not_their_children(sample_project: Path):
    corpus = _corpus(sample_project)
    rows = outline(corpus, corpus.root, kinds=frozenset({ScopeKind.CLASS}))
    assert {m.kind for _, m in rows} == {ScopeKind.CLASS}
    assert {m.name for _, m in rows} >= {"Index", "Store", "Address", "Twin"}


def _walk(scope):
    yield scope
    for child in scope.children():
        yield from _walk(child)
