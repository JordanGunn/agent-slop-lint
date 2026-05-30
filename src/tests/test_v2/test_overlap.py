"""Tests for cross-rule overlap analysis (the Priority view)."""
from __future__ import annotations

from pathlib import Path

from slop.linter.linter import _relativize
from slop.linter.overlap import compute_overlap, family_of
from slop.linter.slop import Slop
from slop.linter.types import RuleResult


def _v(rule: str, file: str, scope=None, symbol=None) -> Slop:
    return Slop(rule=rule, file=file, scope=scope, symbol=symbol, severity="error")


def _rr(rule: str, violations: list[Slop]) -> RuleResult:
    return RuleResult(rule=rule, status="fail", violations=violations)


class TestFamilyOf:
    def test_namespace_collapses(self):
        assert family_of("complexity.cyclomatic") == "complexity"
        assert family_of("complexity.combinatorial") == "complexity"
        assert family_of("lexical.stutter") == "lexical"

    def test_standalone_is_own_family(self):
        assert family_of("coupling") == "coupling"
        assert family_of("hotspots") == "hotspots"


class TestComputeOverlap:
    def test_complexity_family_collapses_to_one(self):
        # one file tripping three complexity.* rules = ONE concern, not three
        rr = {
            "complexity.cyclomatic": _rr("complexity.cyclomatic", [_v("complexity.cyclomatic", "a.py")]),
            "complexity.cognitive": _rr("complexity.cognitive", [_v("complexity.cognitive", "a.py")]),
            "complexity.combinatorial": _rr("complexity.combinatorial", [_v("complexity.combinatorial", "a.py")]),
        }
        targets = compute_overlap(rr, min_families=1)
        assert len(targets) == 1
        assert targets[0].families == ["complexity"]
        assert targets[0].finding_count == 3

    def test_min_families_filters_single_family(self):
        rr = {"coupling": _rr("coupling", [_v("coupling", "a.py"), _v("coupling", "a.py")])}
        assert compute_overlap(rr) == []   # default min_families=2

    def test_ranks_by_distinct_families(self):
        rr = {
            "complexity.cyclomatic": _rr("complexity.cyclomatic", [_v("complexity.cyclomatic", "multi.py"), _v("complexity.cyclomatic", "pair.py")]),
            "lexical.stutter": _rr("lexical.stutter", [_v("lexical.stutter", "multi.py"), _v("lexical.stutter", "pair.py")]),
            "coupling": _rr("coupling", [_v("coupling", "multi.py")]),
        }
        targets = compute_overlap(rr, min_families=2)
        assert [t.file for t in targets] == ["multi.py", "pair.py"]
        assert targets[0].families == ["complexity", "coupling", "lexical"]
        assert targets[1].families == ["complexity", "lexical"]

    def test_symbol_co_fire_surfaced(self):
        rr = {
            "complexity.cyclomatic": _rr("complexity.cyclomatic", [_v("complexity.cyclomatic", "a.py", "function", "foo")]),
            "lexical.stutter": _rr("lexical.stutter", [_v("lexical.stutter", "a.py", "function", "foo")]),
        }
        target = compute_overlap(rr, min_families=2)[0]
        assert target.symbols and target.symbols[0].symbol == "foo"
        assert set(target.symbols[0].families) == {"complexity", "lexical"}

    def test_top_caps_results(self):
        rr = {}
        for i in range(5):
            f = f"f{i}.py"
            rr[f"r{i}a"] = _rr(f"r{i}a", [_v(f"r{i}a", f)])
            rr[f"r{i}b"] = _rr(f"r{i}b", [_v(f"r{i}b", f)])
        assert len(compute_overlap(rr, top=3)) == 3


class TestRelativize:
    def test_absolute_under_root_becomes_relative(self):
        assert _relativize("/repo/slop/a.py", Path("/repo")) == "slop/a.py"

    def test_already_relative_is_kept(self):
        assert _relativize("slop/a.py", Path("/repo")) == "slop/a.py"

    def test_absolute_outside_root_is_kept(self):
        assert _relativize("/other/a.py", Path("/repo")) == "/other/a.py"
