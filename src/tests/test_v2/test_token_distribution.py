"""Tests for the token-distribution diagnostic + ``Lexicon.token_distribution``.

Covers the compute (Zipf fit, hapax spectrum, head concentration) and the
natural-language ``narrate()`` transform that observation output consumes.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

from slop.lexicon.diagnostic.distribution import (
    HAPAX_RATIO_NORM,
    TokenDistribution,
    token_distribution,
)
from slop.tree.tree import Tree


def _lexicon(path: Path):
    t = Tree(path)
    t.scan()
    return t.lexicon


class TestTokenDistributionCompute:
    def test_empty_corpus_is_zeroed(self):
        d = token_distribution(Counter())
        assert d.distinct == 0
        assert d.n == 0
        assert d.hapax_ratio == 0.0
        assert d.top == []

    def test_basic_counts(self):
        d = token_distribution(Counter({"a": 5, "b": 3, "c": 1, "e": 1}))
        assert d.n == 10
        assert d.distinct == 4
        assert d.hapax == 2          # c, e appear once
        assert d.hapax_ratio == 0.5
        assert d.top[0] == ("a", 5)

    def test_spectrum_buckets_freq_of_freq(self):
        # three tokens at count 1, one at count 2, one at count 11 (>10)
        d = token_distribution(
            Counter({"x": 11, "y": 2, "a": 1, "b": 1, "c": 1})
        )
        assert d.spectrum["1"] == 3
        assert d.spectrum["2"] == 1
        assert d.spectrum[">10"] == 1

    def test_zipf_fit_on_clean_power_law(self):
        # counts 100, 50, 33, 25, 20 ~ 100/rank -> alpha near 1, high R^2
        freq = Counter({f"t{r}": round(100 / r) for r in range(1, 12)})
        d = token_distribution(freq)
        assert 0.7 <= d.zipf_alpha <= 1.3
        assert d.zipf_r2 >= 0.9

    def test_head_concentration_is_top10_share(self):
        freq = Counter({f"t{i}": 1 for i in range(20)})
        freq["big"] = 80
        d = token_distribution(freq)
        # big + 9 ones = 89 of 100 occurrences in the top 10
        assert d.head_concentration > 0.8

    def test_as_dict_is_json_shaped(self):
        d = token_distribution(Counter({"a": 3, "b": 1}))
        out = d.as_dict()
        assert out["distinct"] == 2
        assert "norms" in out
        assert out["top"][0] == {"token": "a", "count": 3}


class TestNarrate:
    def test_empty_narration(self):
        assert "empty" in token_distribution(Counter()).narrate().lower()

    def test_healthy_gradient_reads_typical(self):
        freq = Counter({f"t{r}": max(1, round(100 / r)) for r in range(1, 40)})
        text = token_distribution(freq).narrate()
        assert "Zipfian" in text

    def test_dominant_concept_called_out(self):
        freq = Counter({"nodes": 100, "x": 10, "y": 8})
        text = token_distribution(freq).narrate()
        assert "`nodes`" in text and "dominant concept" in text

    def test_hapax_floor_phrased(self):
        text = token_distribution(Counter({"a": 3, "b": 1})).narrate()
        assert "appear exactly once" in text


class TestLexiconViewMethod:
    def test_view_returns_distribution(self, tmp_path: Path):
        (tmp_path / "m.py").write_text(
            "def load_node(node):\n    return node\n"
            "def save_node(node):\n    return node\n"
        )
        d = _lexicon(tmp_path).token_distribution()
        assert isinstance(d, TokenDistribution)
        assert d.distinct > 0
        # `node` is reused, so it should lead the distribution
        assert d.top[0][0] == "node"

    def test_norm_constants_exposed(self):
        assert 0.0 < HAPAX_RATIO_NORM < 1.0


class TestPackageDistributions:
    def _two_pkg_corpus(self, root: Path) -> None:
        # pkg_hi: every identifier token distinct -> high hapax ratio
        (root / "pkg_hi").mkdir()
        (root / "pkg_hi" / "m.py").write_text(
            "def alpha_one(): pass\n"
            "def beta_two(): pass\n"
            "def gamma_three(): pass\n"
            "def delta_four(): pass\n"
        )
        # pkg_lo: one token reused heavily -> low hapax ratio
        (root / "pkg_lo").mkdir()
        (root / "pkg_lo" / "m.py").write_text(
            "def node_load(node): return node\n"
            "def node_save(node): return node\n"
            "def node_walk(node): return node\n"
            "def node_drop(node): return node\n"
        )

    def test_groups_by_package_and_ranks_by_hapax(self, tmp_path: Path):
        self._two_pkg_corpus(tmp_path)
        pds = _lexicon(tmp_path).package_distributions(min_distinct=3)
        names = [pkg for pkg, _ in pds]
        assert set(names) == {"pkg_hi", "pkg_lo"}
        # highest hapax ratio first
        assert names[0] == "pkg_hi"
        assert pds[0][1].hapax_ratio > pds[1][1].hapax_ratio

    def test_min_distinct_floor_drops_small_packages(self, tmp_path: Path):
        self._two_pkg_corpus(tmp_path)
        # floor above either package's vocabulary size -> nothing survives
        pds = _lexicon(tmp_path).package_distributions(min_distinct=999)
        assert pds == []

    def test_descends_into_dominant_subtree(self, tmp_path: Path):
        # scan root above the package root: a dominant `src/` subtree with
        # sibling `docs/`. Grouping must descend into src/ and split its
        # subpackages, not collapse everything into one `src` bucket.
        src = tmp_path / "src"
        (src / "aa").mkdir(parents=True)
        (src / "bb").mkdir(parents=True)
        (src / "aa" / "m.py").write_text(
            "def aa_one(): pass\ndef aa_two(): pass\ndef aa_three(): pass\n"
        )
        (src / "bb" / "m.py").write_text(
            "def bb_one(): pass\ndef bb_two(): pass\ndef bb_three(): pass\n"
        )
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "tiny.py").write_text("x = 1\n")
        pds = _lexicon(tmp_path).package_distributions(min_distinct=2)
        names = {pkg for pkg, _ in pds}
        assert names == {"aa", "bb"}  # descended into src/, split its packages


class _FakeGraph:
    """Stand-in for Structure.dependency_graph(): only `.efferent` is read."""
    def __init__(self, efferent):
        self.efferent = efferent


class TestConceptOwnership:
    def _displaced_corpus(self, root: Path):
        # widget/ DEFINES the concept; rogue/ OWNS the `widget` token by usage
        (root / "widget").mkdir()
        (root / "widget" / "m.py").write_text("class Widget: pass\n")
        (root / "rogue").mkdir()
        (root / "rogue" / "m.py").write_text(
            "def widget_make(): pass\n"
            "def widget_drop(): pass\n"
            "def widget_scan(): pass\n"
        )
        lex = _lexicon(root)
        paths = [str(p) for p, _ in lex.by_file()]
        rogue = next(p for p in paths if "rogue" in p)
        widget = next(p for p in paths if "widget" in p)
        return lex, rogue, widget

    def test_unexplained_displacement_when_no_import(self, tmp_path: Path):
        lex, _rogue, _widget = self._displaced_corpus(tmp_path)
        own = lex.concept_ownership(_FakeGraph({}), top=20)
        w = next(o for o in own if o.token == "widget")
        assert w.owner == "rogue"          # owned by usage, not by definition
        assert w.displaced is True         # `widget` names a package it doesn't own
        assert w.owner_imports_eponymous is False
        assert w.verdict() == "displaced_unexplained"

    def test_import_gate_suppresses_displacement(self, tmp_path: Path):
        lex, rogue, widget = self._displaced_corpus(tmp_path)
        # rogue imports widget -> the owner is a legitimate consumer
        own = lex.concept_ownership(_FakeGraph({rogue: {widget}}), top=20)
        w = next(o for o in own if o.token == "widget")
        assert w.displaced is True
        assert w.owner_imports_eponymous is True
        assert w.verdict() == "displaced_explained"   # gated out, not surfaced

    def test_cohesive_token_not_displaced(self, tmp_path: Path):
        # a token that doesn't name any package is never "displaced"
        (tmp_path / "core").mkdir()
        (tmp_path / "core" / "m.py").write_text(
            "def parse_alpha(): pass\ndef parse_beta(): pass\ndef parse_gamma(): pass\n"
        )
        lex = _lexicon(tmp_path)
        own = lex.concept_ownership(_FakeGraph({}), top=20)
        parse = next(o for o in own if o.token == "parse")
        assert parse.names_package is False
        assert parse.displaced is False
        assert parse.verdict() in {"cohesive", "cross_cutting"}
