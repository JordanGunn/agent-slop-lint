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
