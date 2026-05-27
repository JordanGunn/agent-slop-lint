"""Tests for ``slop.lexicon.diagnostics`` — multi-scope counts, histograms, emit."""
from __future__ import annotations

from pathlib import Path

from slop.linter.rule import Rule
from slop.config import Config
from slop.lexicon.affix import UNIVERSAL_NOISE
from slop.lexicon.diagnostics import (
    DistributionSummary,
    HistogramBin,
    count_violations_by_scope,
    distribution_summary,
    emit_diagnostic_report,
    histogram_buckets,
    log_buckets,
)
from slop.linter import RULE_REGISTRY

LEXICAL_RULES = [r for r in RULE_REGISTRY if r.name.startswith("lexical.")]
from slop.tree.tree import Tree


def _write(root: Path, rel: str, src: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(src)
    return path


# ---------------------------------------------------------------------------
# Histograms
# ---------------------------------------------------------------------------


class TestHistogramBuckets:
    def test_empty_input_returns_empty(self):
        assert histogram_buckets([]) == []

    def test_all_equal_values_yields_single_bin(self):
        bins = histogram_buckets([5.0, 5.0, 5.0])
        assert len(bins) == 1
        assert bins[0].count == 3

    def test_uniform_distribution_evenly_bucketed(self):
        bins = histogram_buckets(list(range(10)), bins=5)
        # Each pair of consecutive ints in one bin → 2 per bin (last
        # bin closes inclusive so 8 and 9 both land in bin 5).
        assert len(bins) == 5
        assert sum(b.count for b in bins) == 10
        for b in bins:
            assert b.count == 2

    def test_bin_count_respected(self):
        bins = histogram_buckets([1.0, 2.0, 3.0, 4.0], bins=2)
        assert len(bins) == 2


class TestLogBuckets:
    def test_log_buckets_groups_by_powers_of_two(self):
        bins = log_buckets([1, 2, 3, 4, 5, 6, 7, 8, 16])
        # [1,2): {1} → 1; [2,4): {2,3} → 2; [4,8): {4,5,6,7} → 4;
        # [8,16): {8} → 1; [16,32): {16} → 1
        edges = {(b.lo, b.hi): b.count for b in bins}
        assert edges[(1.0, 2.0)] == 1
        assert edges[(2.0, 4.0)] == 2
        assert edges[(4.0, 8.0)] == 4
        assert edges[(8.0, 16.0)] == 1
        assert edges[(16.0, 32.0)] == 1

    def test_values_above_max_bin_go_in_open_tail(self):
        bins = log_buckets([1, 1, 9999], max_bin_exp=3)
        # max_bin_exp=3 → final bin is [8, inf)
        tail = next(b for b in bins if b.hi == float("inf"))
        assert tail.count == 1
        assert tail.lo == 8.0

    def test_log_buckets_drops_below_one(self):
        bins = log_buckets([0, 1, 2])
        # 0 dropped; 1 → [1,2); 2 → [2,4)
        assert sum(b.count for b in bins) == 2


class TestDistributionSummary:
    def test_basic_stats_correct(self):
        d = distribution_summary([1.0, 2.0, 3.0, 4.0, 5.0], name="x")
        assert d.n == 5
        assert d.mean == 3.0
        assert d.median == 3.0
        assert d.max == 5.0

    def test_p90_is_near_top(self):
        d = distribution_summary([float(i) for i in range(1, 11)], name="x")
        # n=10, p90_idx = int(0.9 * 9) = 8 → value at index 8 = 9.0
        assert d.p90 == 9.0

    def test_empty_input_returns_zero_summary(self):
        d = distribution_summary([], name="x")
        assert d.n == 0
        assert d.max == 0.0


# ---------------------------------------------------------------------------
# Multi-scope violation measurement
# ---------------------------------------------------------------------------


class TestCountViolationsByScope:
    def _corpus(self, tmp_path: Path) -> Tree:
        # Create a corpus that fires lexical.cowards (v1 suffix) and
        # lexical.verbosity (long names) so multiple rules participate.
        _write(tmp_path, "pkg_a/x.py",
               "def process_data_v1(): pass\n"
               "def parse_request_handler_helper(): pass\n")
        _write(tmp_path, "pkg_b/y.py",
               "def render_v2(): pass\n")
        t = Tree(tmp_path)
        t.scan()
        return t

    def test_file_scope_buckets_per_file(self, tmp_path: Path):
        t = self._corpus(tmp_path)
        cfgs: dict = {}  # default-enabled stand-ins for each rule
        sc = Config(rules={}, languages=["python"], root=str(tmp_path))
        counts = count_violations_by_scope(
            t.lexicon, LEXICAL_RULES, rule_configs=cfgs, slop_config=sc,
            scope="file", root=tmp_path,
        )
        # Both files contain coward findings (_v1 / _v2 suffix). Verify
        # at least one count per file shows up.
        files = {c.key for c in counts if c.rule == "lexical.cowards"}
        assert "pkg_a/x.py" in files
        assert "pkg_b/y.py" in files

    def test_root_scope_single_bucket(self, tmp_path: Path):
        t = self._corpus(tmp_path)
        cfgs: dict = {}
        sc = Config(rules={}, languages=["python"], root=str(tmp_path))
        counts = count_violations_by_scope(
            t.lexicon, LEXICAL_RULES, rule_configs=cfgs, slop_config=sc,
            scope="root", root=tmp_path,
        )
        # Every entry should have key="<root>"
        assert all(c.key == "<root>" for c in counts)

    def test_package_scope_buckets_per_parent_dir(self, tmp_path: Path):
        t = self._corpus(tmp_path)
        cfgs: dict = {}
        sc = Config(rules={}, languages=["python"], root=str(tmp_path))
        counts = count_violations_by_scope(
            t.lexicon, LEXICAL_RULES, rule_configs=cfgs, slop_config=sc,
            scope="package", root=tmp_path,
        )
        pkgs = {c.key for c in counts if c.rule == "lexical.cowards"}
        assert "pkg_a" in pkgs
        assert "pkg_b" in pkgs


# ---------------------------------------------------------------------------
# Composite report emission
# ---------------------------------------------------------------------------


class TestEmitDiagnosticReport:
    def test_minimal_report_shape(self, tmp_path: Path):
        _write(tmp_path, "a.py",
               "def parse_pdf(data): pass\n"
               "def export_pdf(data): pass\n"
               "def render_pdf(data): pass\n")
        t = Tree(tmp_path)
        t.scan()
        report = emit_diagnostic_report(
            t.lexicon, exclude_tokens=UNIVERSAL_NOISE,
        )
        assert report["corpus"]["files"] == 1
        assert report["corpus"]["callables"] == 3
        assert "token_occurrence_count" in report["distributions"]
        assert "packet_size_callable_scope" in report["distributions"]
        assert "packets" in report
        assert "callable_scope" in report["packets"]
        assert "file_scope" in report["packets"]

    def test_with_class_vocabularies_splits_packets(self, tmp_path: Path):
        # Force a packet to fire: a class with method tokens that
        # appear together in 5+ callables.
        for i in range(6):
            _write(tmp_path, f"f{i}.py",
                   f"def fn_{i}(excludes, hidden, ignore, globs): pass\n")
        t = Tree(tmp_path)
        t.scan()
        vocabs = t.structure.class_vocabularies()
        report = emit_diagnostic_report(
            t.lexicon,
            class_vocabularies=vocabs,
            exclude_tokens=UNIVERSAL_NOISE,
            packet_min_bags=5, packet_min_association=0.7,
        )
        assert "pathological" in report["packets"]["callable_scope"]
        assert "conventional" in report["packets"]["callable_scope"]
        # No classes exist → no conventional packets.
        assert report["packets"]["callable_scope"]["conventional"] == []

    def test_with_rules_emits_violations_section(self, tmp_path: Path):
        _write(tmp_path, "a.py", "def proc_v1(): pass\ndef proc_v2(): pass\n")
        t = Tree(tmp_path)
        t.scan()
        sc = Config(rules={}, languages=["python"], root=str(tmp_path))
        report = emit_diagnostic_report(
            t.lexicon, rule_defs=LEXICAL_RULES,
            rule_configs={}, slop_config=sc, root=tmp_path,
        )
        assert "violations_by_scope" in report
        for axis in ("file", "package", "root", "callable"):
            assert axis in report["violations_by_scope"]

    def test_report_is_json_serialisable(self, tmp_path: Path):
        import json
        _write(tmp_path, "a.py", "def parse(): pass\n")
        t = Tree(tmp_path)
        t.scan()
        report = emit_diagnostic_report(t.lexicon, exclude_tokens=UNIVERSAL_NOISE)
        # Should not raise
        s = json.dumps(report)
        assert len(s) > 0
