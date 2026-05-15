"""Tests for the v2 ``structural.magic_literals`` rule.

Exercises ``run_magic_literals`` end-to-end via the Structure view.
Verifies the rule detects distinct non-trivial numeric literals in
function bodies across all 11 supported languages, that the trivial
set is honoured, and that nested callables get their own metric
(don't pollute the parent's count).
"""
from __future__ import annotations

from pathlib import Path

from slop.config.models import RuleConfig, SlopConfig
from slop.structure.rules.magic_literals import run_magic_literals
from slop.tree.tree import Tree


def _rc(threshold: int = 3) -> RuleConfig:
    return RuleConfig(enabled=True, severity="warning", params={"threshold": threshold})


def _sc(tmp_path: Path) -> SlopConfig:
    return SlopConfig(root=str(tmp_path))


def _run(tmp_path: Path, threshold: int = 3):
    cb = Tree(tmp_path)
    cb.scan()
    return run_magic_literals(cb.structure, _rc(threshold), _sc(tmp_path))


class TestTrivials:
    def test_trivial_ints_excluded(self, tmp_path: Path):
        # 0, 1, -1, 2 all trivial → count = 0
        (tmp_path / "a.py").write_text(
            "def f():\n    return 0 + 1 + 2 + (-1)\n"
        )
        result = _run(tmp_path, threshold=0)
        assert result.status == "pass"

    def test_trivial_floats_excluded(self, tmp_path: Path):
        # 0.0, 0.5, 1.0, 2.0, 100.0 all trivial → count = 0
        (tmp_path / "a.py").write_text(
            "def f():\n    return 0.0 + 0.5 + 1.0 + 2.0 + 100.0\n"
        )
        result = _run(tmp_path, threshold=0)
        assert result.status == "pass"

    def test_non_trivial_int_counted(self, tmp_path: Path):
        # 42 alone exceeds threshold=0
        (tmp_path / "a.py").write_text("def f():\n    return 42\n")
        result = _run(tmp_path, threshold=0)
        assert result.status == "fail"
        assert result.violations[0].value == 1


class TestDistinctCounting:
    def test_repeated_literal_counts_once(self, tmp_path: Path):
        (tmp_path / "a.py").write_text(
            "def f():\n    return 42 + 42 + 42\n"
        )
        # All "42" — one distinct non-trivial value.
        result = _run(tmp_path, threshold=0)
        assert result.status == "fail"
        assert result.violations[0].value == 1

    def test_distinct_literals_counted_separately(self, tmp_path: Path):
        (tmp_path / "a.py").write_text(
            "def f():\n    return 42 + 86400 + 365 + 1024\n"
        )
        result = _run(tmp_path, threshold=2)
        assert result.status == "fail"
        # 4 distinct non-trivials > threshold 2
        assert result.violations[0].value == 4


class TestNestedCallables:
    def test_nested_function_metric_separately(self, tmp_path: Path):
        # Outer has 4 magic numbers; inner has 0.
        # Each callable gets its OWN count — inner doesn't inherit outer's.
        (tmp_path / "a.py").write_text(
            "def outer():\n"
            "    a = 42\n"
            "    b = 86400\n"
            "    c = 365\n"
            "    d = 1024\n"
            "    def inner():\n"
            "        return 0\n"
            "    return inner()\n"
        )
        result = _run(tmp_path, threshold=2)
        # outer: 4 distinct > 2 → fail. inner: 0 → no contribution.
        assert result.status == "fail"
        outer = next(v for v in result.violations if v.symbol == "outer")
        assert outer.value == 4


class TestMultiLanguage:
    """Each fixture has the same 5-magic-literal shape — count=5 across
    every supported language, verifying ``numeric_literal_nodes()``
    declarations on every grammar."""

    FIXTURES = {
        "py.py": "def discount(d):\n    if d>30: return 100*d/365\n    if d>7: return 50\n    return 7\n",
        "js.js": "function discount(d) {\n  if (d>30) return 100*d/365;\n  if (d>7) return 50;\n  return 7;\n}\n",
        "ts.ts": "function discount(d:number) {\n  if (d>30) return 100*d/365;\n  if (d>7) return 50;\n  return 7;\n}\n",
        "g.go": "package p\nfunc Discount(d int) int {\n  if d>30 { return 100*d/365 }\n  if d>7 { return 50 }\n  return 7\n}\n",
        "r.rs": "fn discount(d:i32)->i32 {\n  if d>30 { return 100*d/365; }\n  if d>7 { return 50; }\n  7\n}\n",
        "A.java": "class A {\n  int discount(int d) {\n    if (d>30) return 100*d/365;\n    if (d>7) return 50;\n    return 7;\n  }\n}\n",
        "B.cs": "class B {\n  int Discount(int d) {\n    if (d>30) return 100*d/365;\n    if (d>7) return 50;\n    return 7;\n  }\n}\n",
        "c.c": "int discount(int d) {\n  if (d>30) return 100*d/365;\n  if (d>7) return 50;\n  return 7;\n}\n",
        "p.cpp": "int discount(int d) {\n  if (d>30) return 100*d/365;\n  if (d>7) return 50;\n  return 7;\n}\n",
        "rb.rb": "def discount(d)\n  return 100*d/365 if d>30\n  return 50 if d>7\n  7\nend\n",
        "jl.jl": "function discount(d)\n  d>30 && return 100*d/365\n  d>7 && return 50\n  7\nend\n",
    }

    def test_all_languages_parity(self, tmp_path: Path):
        for name, content in self.FIXTURES.items():
            (tmp_path / name).write_text(content)
        result = _run(tmp_path, threshold=0)
        # Every file has 5 distinct non-trivial magic literals: 30, 100, 365, 7, 50.
        # All 11 fixtures should be flagged.
        flagged_files = {v.file for v in result.violations}
        assert len(flagged_files) == 11
        for v in result.violations:
            assert v.value == 5, f"{v.file}/{v.symbol}: expected 5, got {v.value}"


class TestThresholdAndFormatting:
    def test_below_threshold_passes(self, tmp_path: Path):
        (tmp_path / "a.py").write_text("def f():\n    return 42 + 365\n")
        # 2 distinct non-trivials; threshold=3 → pass
        result = _run(tmp_path, threshold=3)
        assert result.status == "pass"

    def test_violations_sorted_by_count_desc(self, tmp_path: Path):
        (tmp_path / "many.py").write_text(
            "def many():\n    return 42 + 86400 + 365 + 1024 + 999\n"
        )
        (tmp_path / "few.py").write_text(
            "def few():\n    return 42 + 86400 + 365 + 1024\n"
        )
        result = _run(tmp_path, threshold=2)
        # many=5 should sort before few=4
        assert result.violations[0].symbol == "many"
        assert result.violations[1].symbol == "few"

    def test_rule_name_is_structural(self, tmp_path: Path):
        # Confirms the v2.0 relocation: rule emits structural.magic_literals,
        # not the legacy information.magic_literals.
        (tmp_path / "a.py").write_text("def f():\n    return 42 + 365 + 1024 + 999\n")
        result = _run(tmp_path, threshold=2)
        assert result.violations[0].rule == "structural.magic_literals"


class TestCompatLegacyName:
    """The legacy `information.magic_literals` name resolves to the v2
    canonical `structural.magic_literals` via slop._compat.
    """

    def test_legacy_rule_name_canonicalises(self):
        from slop._compat import canonical_rule_name
        canonical, was_legacy = canonical_rule_name("information.magic_literals")
        assert canonical == "structural.magic_literals"
        assert was_legacy is True

    def test_section_comments_legacy_name_is_removed(self):
        from slop._compat import REMOVED_RULES
        assert "information.section_comments" in REMOVED_RULES
        assert "removed in v2.0" in REMOVED_RULES["information.section_comments"]
