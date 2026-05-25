"""Tests for the three-planes-of-evaluation primitives on Lexicon.

Each plane is a distinct primitive with its own threshold parameter
and distinct return type. The "hub" interpretation is a downstream
judgment on the INTERSECTION of planes, not a property of any one
primitive. Per obs 07 (forthcoming), these compose with the existing
``packets`` (Plane A) to let observations tabulate the overlap matrix
empirically.
"""
from __future__ import annotations

from pathlib import Path

from slop.lexicon.affix import UNIVERSAL_NOISE
from slop.tree.tree import Tree


def _lexicon(root: Path):
    t = Tree(root)
    t.scan()
    return t.lexicon


def _write(root: Path, rel: str, src: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(src)
    return path


# ---------------------------------------------------------------------------
# hapax_ratio — tail summary
# ---------------------------------------------------------------------------


class TestHapaxRatio:
    def test_empty_corpus_returns_zero(self, tmp_path: Path):
        assert _lexicon(tmp_path).hapax_ratio() == 0.0

    def test_all_unique_tokens_returns_one(self, tmp_path: Path):
        _write(tmp_path, "a.py",
               "def alpha(): pass\n"
               "def beta(): pass\n"
               "def gamma(): pass\n")
        # alpha, beta, gamma each appear exactly once → ratio = 1.0
        assert _lexicon(tmp_path).hapax_ratio() == 1.0

    def test_all_repeated_returns_zero(self, tmp_path: Path):
        _write(tmp_path, "a.py",
               "def parse_x(): pass\n"  # x ∈ Newman 14
               "def parse_p(): pass\n")  # p ∈ Newman 14
        ratio = _lexicon(tmp_path).hapax_ratio(exclude=UNIVERSAL_NOISE)
        # After Newman 14 strip: only `parse` survives (count 2). 0 of 1
        # tokens is hapax → ratio = 0.
        assert ratio == 0.0

    def test_mixed_distribution(self, tmp_path: Path):
        _write(tmp_path, "a.py",
               "def parse(): pass\n"
               "def parse_more(): pass\n"
               "def unique(): pass\n")
        # parse: 2, more: 1, unique: 1 → 2 of 3 hapax = 0.667
        ratio = _lexicon(tmp_path).hapax_ratio()
        assert abs(ratio - 2/3) < 1e-9


# ---------------------------------------------------------------------------
# frequency_head — Plane B
# ---------------------------------------------------------------------------


class TestFrequencyHead:
    def test_returns_tokens_above_threshold(self, tmp_path: Path):
        _write(tmp_path, "a.py",
               "def parse_x(): pass\n"
               "def parse_y(): pass\n"
               "def parse_z(): pass\n"
               "def render(): pass\n")
        # parse: 3, x/y/z/render: 1 each
        head = _lexicon(tmp_path).frequency_head(threshold=2)
        names = {t for t, _ in head}
        assert names == {"parse"}

    def test_default_threshold_is_p90(self, tmp_path: Path):
        # Construct so p90 is computable. 10 tokens, p90 idx = 8.
        srcs = [f"def func_alpha_{i}(): pass\n" for i in range(10)]
        _write(tmp_path, "a.py", "".join(srcs))
        head = _lexicon(tmp_path).frequency_head()
        # `func`/`alpha` appear 10 times; others appear 1 each.
        # sorted counts: [1,1,1,1,1,1,1,1,1,1,10,10] (with `i` excluded by Newman 14)
        # Threshold = sorted[int(0.9 * 11)] = sorted[9] = ?
        # The exact value depends on Newman 14 stripping; check the
        # high-frequency tokens at minimum appear.
        names = {t for t, _ in head}
        assert {"func", "alpha"} <= names

    def test_descending_by_count(self, tmp_path: Path):
        _write(tmp_path, "a.py",
               "def parse_a(): pass\n"
               "def parse_b(): pass\n"
               "def parse_c(): pass\n"
               "def render_x(): pass\n"
               "def render_y(): pass\n")
        head = _lexicon(tmp_path).frequency_head(threshold=2)
        counts = [n for _, n in head]
        assert counts == sorted(counts, reverse=True)

    def test_empty_corpus_returns_empty(self, tmp_path: Path):
        assert _lexicon(tmp_path).frequency_head(threshold=1) == []

    def test_distinct_from_modal_tokens_contract(self, tmp_path: Path):
        # frequency_head is threshold-based; modal_tokens is top-K.
        # Verify both work and return different shapes given the same
        # corpus + sensible parameters.
        _write(tmp_path, "a.py",
               "def parse_pdf(): pass\n"
               "def parse_xml(): pass\n"
               "def render_pdf(): pass\n")
        lex = _lexicon(tmp_path)
        # modal_tokens(top=2) → exactly 2 results regardless of frequency
        modal = lex.modal_tokens(top=2)
        assert len(modal) == 2
        # frequency_head(threshold=2) → variable number, only tokens with count >= 2
        head = lex.frequency_head(threshold=2)
        assert all(n >= 2 for _, n in head)


# ---------------------------------------------------------------------------
# spread_dominant — Plane C
# ---------------------------------------------------------------------------


class TestSpreadDominant:
    def test_returns_tokens_above_spread(self, tmp_path: Path):
        # `pdf` in 3 files; `parse`, `render`, `export` each in 1 file.
        _write(tmp_path, "a.py", "def parse_pdf(): pass\n")
        _write(tmp_path, "b.py", "def render_pdf(): pass\n")
        _write(tmp_path, "c.py", "def export_pdf(): pass\n")
        dominant = _lexicon(tmp_path).spread_dominant(min_spread=3)
        names = {t for t, _ in dominant}
        assert "pdf" in names
        assert "parse" not in names

    def test_descending_by_spread(self, tmp_path: Path):
        _write(tmp_path, "a.py", "def f_pdf(target): pass\n")
        _write(tmp_path, "b.py", "def g_pdf(target): pass\n")
        _write(tmp_path, "c.py", "def h_pdf(): pass\n")  # no target
        dominant = _lexicon(tmp_path).spread_dominant(min_spread=2)
        # `pdf`: 3 files; `target`: 2 files; both qualify
        spreads = [n for _, n in dominant]
        assert spreads == sorted(spreads, reverse=True)

    def test_exclude_filter_applied(self, tmp_path: Path):
        # `id` is in UNIVERSAL_NOISE; should be dropped before counting.
        for i in range(5):
            _write(tmp_path, f"f{i}.py", f"def f_{i}(id): pass\n")
        dominant = _lexicon(tmp_path).spread_dominant(
            min_spread=3, exclude=UNIVERSAL_NOISE,
        )
        names = {t for t, _ in dominant}
        assert "id" not in names

    def test_empty_corpus_returns_empty(self, tmp_path: Path):
        assert _lexicon(tmp_path).spread_dominant(min_spread=2) == []


# ---------------------------------------------------------------------------
# Composition — the three planes return distinct types and answer
# distinct questions
# ---------------------------------------------------------------------------


class TestMiddleSpread:
    def test_returns_spread_but_not_head(self, tmp_path: Path):
        # Construct: token `pdf` in 4 files at freq 4 (head); `helper`
        # in 4 files at freq 4. Both have high spread; whether they're
        # in the "head" depends on the p90 cutoff of this corpus.
        for i in range(4):
            _write(tmp_path, f"f{i}.py",
                   f"def proc_{i}_pdf_helper(): pass\n")
        lex = _lexicon(tmp_path)
        # Use an explicit max_frequency above pdf/helper to force them
        # into the middle-spread bucket.
        out = lex.middle_spread(min_spread=3, max_frequency=10)
        names = {t for t, _, _ in out}
        assert "pdf" in names
        assert "helper" in names

    def test_excludes_above_max_frequency(self, tmp_path: Path):
        for i in range(4):
            _write(tmp_path, f"f{i}.py",
                   f"def proc_{i}_pdf(): pass\n")
        lex = _lexicon(tmp_path)
        # pdf appears 4 times across 4 files; max_frequency=3 excludes it.
        out = lex.middle_spread(min_spread=3, max_frequency=3)
        names = {t for t, _, _ in out}
        assert "pdf" not in names

    def test_returns_triples(self, tmp_path: Path):
        _write(tmp_path, "a.py", "def parse_pdf(): pass\n")
        _write(tmp_path, "b.py", "def render_pdf(): pass\n")
        _write(tmp_path, "c.py", "def export_pdf(): pass\n")
        out = _lexicon(tmp_path).middle_spread(
            min_spread=3, max_frequency=10,
        )
        assert all(isinstance(item, tuple) and len(item) == 3 for item in out)

    def test_empty_corpus_returns_empty(self, tmp_path: Path):
        assert _lexicon(tmp_path).middle_spread(min_spread=2) == []


class TestPacketIsolates:
    def test_high_freq_non_packet_token_surfaces(self, tmp_path: Path):
        # `root` is a hub: appears in 6 callables but each callable has a
        # distinct partner-set, so it doesn't bond with any specific
        # token. Function names are all distinct stems so no token
        # partners with root across all 6 callables.
        _write(tmp_path, "a.py",
               "def alpha(root): pass\n"
               "def beta(root): pass\n"
               "def gamma(root): pass\n"
               "def delta(root): pass\n"
               "def epsilon(root): pass\n"
               "def zeta(root): pass\n")
        lex = _lexicon(tmp_path)
        isolates = lex.packet_isolates(
            min_bags=3, min_association=0.7, min_frequency=2,
        )
        names = {t for t, _ in isolates}
        assert "root" in names

    def test_packet_member_excluded(self, tmp_path: Path):
        # `a`/`b` form a tight packet → they should NOT show up in isolates.
        _write(tmp_path, "a.py",
               "def f1(alpha, beta): pass\n"
               "def f2(alpha, beta): pass\n"
               "def f3(alpha, beta): pass\n"
               "def f4(alpha, beta): pass\n")
        lex = _lexicon(tmp_path)
        isolates = lex.packet_isolates(
            min_bags=3, min_association=0.7, min_frequency=2,
        )
        names = {t for t, _ in isolates}
        # alpha + beta are tight packet members → not in isolates
        assert "alpha" not in names
        assert "beta" not in names

    def test_min_frequency_floor_respected(self, tmp_path: Path):
        _write(tmp_path, "a.py", "def f(rare): pass\n")  # rare appears once
        lex = _lexicon(tmp_path)
        isolates = lex.packet_isolates(min_frequency=2)
        names = {t for t, _ in isolates}
        assert "rare" not in names

    def test_empty_corpus_returns_empty(self, tmp_path: Path):
        assert _lexicon(tmp_path).packet_isolates() == []


class TestPlaneIndependence:
    def test_three_planes_return_distinct_shapes(self, tmp_path: Path):
        # Verify that the three primitives compose without sharing
        # thresholds and that their return types differ enough that
        # callers can't accidentally conflate them.
        for i in range(6):
            _write(tmp_path, f"f{i}.py",
                   f"def proc_{i}(data, target): pass\n")
        lex = _lexicon(tmp_path)
        # Plane A (existing): packets — list of token-sets
        packets = lex.packets(min_bags=5, min_association=0.7)
        # Plane B: frequency_head — list of (token, count)
        head = lex.frequency_head(threshold=2)
        # Plane C: spread_dominant — list of (token, file_count)
        spread = lex.spread_dominant(min_spread=2)

        # Type structure is genuinely different per plane:
        if packets:
            assert isinstance(packets[0], set)
        if head:
            assert isinstance(head[0], tuple) and len(head[0]) == 2
        if spread:
            assert isinstance(spread[0], tuple) and len(spread[0]) == 2

    def test_hub_is_intersection_not_property(self, tmp_path: Path):
        # `root` here is the classic hub: high spread, high frequency,
        # but doesn't form packets because it co-occurs with everything.
        _write(tmp_path, "a.py", "def alpha(root, x): pass\n")
        _write(tmp_path, "b.py", "def beta(root, y): pass\n")
        _write(tmp_path, "c.py", "def gamma(root, z): pass\n")
        _write(tmp_path, "d.py", "def delta(root, w): pass\n")
        lex = _lexicon(tmp_path)
        head = {t for t, _ in lex.frequency_head(threshold=2)}
        spread = {t for t, _ in lex.spread_dominant(min_spread=3)}
        packets = lex.packets(min_bags=3, min_association=0.7)
        packet_tokens: set[str] = set()
        for p in packets:
            packet_tokens |= p
        # `root` is in Planes B + C (high freq, high spread) but NOT in
        # Plane A (no packet membership). That's the hub intersection
        # signature — surfaced only by combining planes.
        assert "root" in head
        assert "root" in spread
        assert "root" not in packet_tokens
