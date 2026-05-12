"""Tests for ``slop.lexicon.view.Lexicon``."""
from __future__ import annotations

from pathlib import Path

from slop.tree.tree import Tree


def _lexicon(path: Path):
    cb = Tree(path)
    cb.scan()
    return cb.lexicon


class TestFirstParamClusters:
    def test_cluster_corpus_yields_one_cluster_on_node(self, cluster_corpus: Path):
        lex = _lexicon(cluster_corpus)
        clusters = lex.first_param_clusters(min_cluster=3, root=cluster_corpus)
        # All 4 functions share `node` as their first parameter.
        cluster_params = {c.parameter_name for c in clusters}
        assert "node" in cluster_params

    def test_cluster_contains_all_members(self, cluster_corpus: Path):
        lex = _lexicon(cluster_corpus)
        clusters = lex.first_param_clusters(min_cluster=3, root=cluster_corpus)
        node_clusters = [c for c in clusters if c.parameter_name == "node"]
        assert len(node_clusters) == 1
        assert len(node_clusters[0].members) == 4

    def test_min_cluster_threshold_filters_smaller(self, cluster_corpus: Path):
        lex = _lexicon(cluster_corpus)
        # With min_cluster=5 (one above the 4 we have), no clusters survive.
        clusters = lex.first_param_clusters(min_cluster=5, root=cluster_corpus)
        assert not [c for c in clusters if c.parameter_name == "node"]


class TestSlicing:
    def test_under_returns_new_lexicon(self, tiny_corpus: Path):
        lex = _lexicon(tiny_corpus)
        narrowed = lex.under(path=str(tiny_corpus / "a.py"))
        assert narrowed is not lex


class TestWalk:
    def test_walk_yields_occurrences(self, tiny_corpus: Path):
        lex = _lexicon(tiny_corpus)
        occurrences = list(lex.walk())
        # tiny_corpus has many identifiers; ensure non-empty.
        assert len(occurrences) > 0
