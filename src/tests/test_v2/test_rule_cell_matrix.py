"""Tests for the rule × cell cross-tabulation (obs 09 infrastructure)."""
from __future__ import annotations

from pathlib import Path

from slop.linter.rule import Rule
from slop.config import Config
from slop.lexicon.affix import UNIVERSAL_NOISE
from slop.lexicon.diagnostic import (
    ViolationCell,
    format_cells,
    tabulate_cells,
    with_cells,
)
from slop.linter import RULE_REGISTRY

LEXICAL_RULES = [r for r in RULE_REGISTRY if r.name.startswith("lexical.")]
from slop.tree.tree import Tree


def _write(root: Path, rel: str, src: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(src)
    return path


def _setup(tmp_path: Path):
    t = Tree(tmp_path)
    t.scan()
    sc = Config(rules={}, languages=["python"], root=str(tmp_path))
    return t, sc


class TestViolationsWithCells:
    def test_emits_one_record_per_violation(self, tmp_path: Path):
        # Two verbosity-rule fires (long function names).
        _write(tmp_path, "a.py",
               "def process_alpha_beta_gamma_delta(): pass\n"
               "def process_alpha_beta_gamma_epsilon(): pass\n")
        t, sc = _setup(tmp_path)
        records = with_cells(
            t.lexicon, LEXICAL_RULES,
            rule_configs={}, slop_config=sc,
            frequency_threshold=2, spread_threshold=1,
        )
        verbosity = [r for r in records if r.rule == "lexical.verbosity"]
        assert len(verbosity) == 2
        assert all(r.cell != "" for r in verbosity)

    def test_cell_assignment_from_symbol_tokens(self, tmp_path: Path):
        # Construct a corpus where `pdf` lands in plane C (spread):
        # use long enough names that verbosity (>3 tokens) fires.
        for i in range(5):
            _write(tmp_path, f"f{i}.py",
                   f"def pdf_extra_long_handler_processor_helper_{i}(): pass\n")
        t, sc = _setup(tmp_path)
        records = with_cells(
            t.lexicon, LEXICAL_RULES,
            rule_configs={}, slop_config=sc,
            frequency_threshold=4, spread_threshold=3,
        )
        verbosity_records = [r for r in records if r.rule == "lexical.verbosity"]
        assert len(verbosity_records) > 0
        assert all(len(r.tokens) > 0 for r in verbosity_records)

    def test_record_carries_full_provenance(self, tmp_path: Path):
        _write(tmp_path, "a.py", "def process_alpha_beta_gamma_delta(): pass\n")
        t, sc = _setup(tmp_path)
        records = with_cells(
            t.lexicon, LEXICAL_RULES,
            rule_configs={}, slop_config=sc,
        )
        rec = next(r for r in records if r.rule == "lexical.verbosity")
        # ViolationCell carries enough fields to find the violation in source
        assert rec.symbol == "process_alpha_beta_gamma_delta"
        assert rec.file.endswith("a.py")
        assert rec.severity in ("info", "warning", "error")
        assert "process" in rec.tokens

    def test_no_violations_returns_empty(self, tmp_path: Path):
        # Clean fixture — should produce zero or minimal violations.
        _write(tmp_path, "a.py", "def f(): pass\n")
        t, sc = _setup(tmp_path)
        records = with_cells(
            t.lexicon, LEXICAL_RULES,
            rule_configs={}, slop_config=sc,
        )
        # No lexical violations on a single trivial function.
        assert all(r.rule != "lexical.verbosity" for r in records)


class TestCellPriority:
    def test_packet_bearing_cell_wins_over_spread_only(self, tmp_path: Path):
        # Construct so the symbol has BOTH a packet-bearing token and a
        # spread-only token; primary cell should be the packet-bearing one.
        # Use a packet of (alpha, beta) appearing in 4+ callables.
        _write(tmp_path, "a.py",
               "def f1(alpha, beta): pass\n"
               "def f2(alpha, beta): pass\n"
               "def f3(alpha, beta): pass\n"
               "def f4(alpha, beta): pass\n")
        for i in range(5):
            _write(tmp_path, f"g{i}.py", f"def g_pdf_{i}(): pass\n")
        # `pdf` spreads across 5 files but isn't in any packet.
        # `alpha`/`beta` are in a packet.
        # A hypothetical symbol "alpha_pdf" would have one packet-token
        # (alpha) and one spread-token (pdf). Verify the classifier picks
        # the packet cell.
        from slop.lexicon.diagnostic.violations import _pick_primary_cell
        t, _ = _setup(tmp_path)
        packets = t.lexicon.packets(min_bags=3, min_association=0.7)
        plane_a: set = set()
        for p in packets:
            plane_a |= p
        plane_b = {tok for tok, _ in t.lexicon.frequency_head(threshold=2)}
        plane_c = {tok for tok, _ in t.lexicon.spread_dominant(min_spread=3)}
        # Need 'alpha' in plane_a, 'pdf' in plane_c at minimum
        assert "alpha" in plane_a or "beta" in plane_a
        # Composite-symbol token list:
        cell, primary = _pick_primary_cell(
            ["alpha", "pdf"],
            plane_a=plane_a, plane_b=plane_b, plane_c=plane_c,
        )
        # Packet token wins; cell starts with 'A'
        assert cell.startswith("A")


class TestTabulateAndFormat:
    def test_tabulate_groups_by_rule_cell(self, tmp_path: Path):
        _write(tmp_path, "a.py",
               "def process_v1(): pass\n"
               "def process_v2(): pass\n")
        t, sc = _setup(tmp_path)
        records = with_cells(
            t.lexicon, LEXICAL_RULES, rule_configs={}, slop_config=sc,
        )
        grid = tabulate_cells(records)
        # Every (rule, cell) key should be a tuple of two strings
        assert all(isinstance(k, tuple) and len(k) == 2 for k in grid.keys())
        # Cells should be valid 3-char codes
        for _, cell in grid.keys():
            assert len(cell) == 3
            assert all(c in "ABC-" for c in cell)

    def test_format_produces_readable_table(self, tmp_path: Path):
        _write(tmp_path, "a.py",
               "def process_v1(): pass\n"
               "def process_v2(): pass\n")
        t, sc = _setup(tmp_path)
        records = with_cells(
            t.lexicon, LEXICAL_RULES, rule_configs={}, slop_config=sc,
        )
        table = format_cells(records, LEXICAL_RULES)
        # Table contains every cell code in the header
        for cell in ("ABC", "AB-", "A-C", "A--", "-BC", "-B-", "--C", "---"):
            assert cell in table
        # Table contains every rule name
        for r in LEXICAL_RULES:
            assert r.name in table

    def test_as_dict_is_json_friendly(self, tmp_path: Path):
        import json
        _write(tmp_path, "a.py", "def process_v1(): pass\n")
        t, sc = _setup(tmp_path)
        records = with_cells(
            t.lexicon, LEXICAL_RULES, rule_configs={}, slop_config=sc,
        )
        for rec in records:
            d = rec.as_dict()
            json.dumps(d)  # should not raise
