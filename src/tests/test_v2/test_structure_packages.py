"""Tests for ``Structure.packages`` — Martin 1994 D' classification.

These are unit tests on the view method directly. Per-language abstractness
classification is verified in ``test_rules/test_architecture.py``; here we
focus on the zone logic and the package-level coupling aggregation.
"""
from __future__ import annotations

from pathlib import Path

from slop.tree.tree import Tree


def _packages(tmp_path: Path):
    t = Tree(tmp_path)
    t.scan()
    return t.structure.packages(tmp_path)


# ---------------------------------------------------------------------------
# Zone classification
# ---------------------------------------------------------------------------


class TestZones:
    def test_unknown_when_no_coupling(self, tmp_path: Path):
        # One package, no inter-package imports → Ca=Ce=0 → I undefined → unknown.
        pkg = tmp_path / "pkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "a.py").write_text("x = 1\n")
        pkgs = _packages(tmp_path)
        assert len(pkgs) == 1
        assert pkgs[0].zone == "unknown"
        assert pkgs[0].instability is None
        assert pkgs[0].abstractness is None

    def test_pain_when_stable_and_concrete(self, tmp_path: Path):
        # ``leaf`` is depended on by two callers, depends on nothing →
        # Ca=2, Ce=0 → I=0. No abstract types → A=0. Zone = pain.
        for name in ("a", "b"):
            d = tmp_path / name
            d.mkdir()
            (d / "__init__.py").write_text("from leaf import x\n")
        leaf = tmp_path / "leaf"
        leaf.mkdir()
        (leaf / "__init__.py").write_text("class T:\n    pass\nx = 1\n")
        pkgs = {p.name: p for p in _packages(tmp_path)}
        leaf_p = pkgs["leaf"]
        assert leaf_p.ca == 2
        assert leaf_p.ce == 0
        assert leaf_p.zone == "pain"

    def test_uselessness_when_unstable_and_abstract(self, tmp_path: Path):
        # ``top`` imports leaf + has only an ABC subclass → high I, high A.
        leaf = tmp_path / "leaf"
        leaf.mkdir()
        (leaf / "__init__.py").write_text("x = 1\n")
        top = tmp_path / "top"
        top.mkdir()
        (top / "__init__.py").write_text(
            "from leaf import x\n"
            "from abc import ABC, abstractmethod\n"
            "class Shape(ABC):\n"
            "    @abstractmethod\n"
            "    def area(self): pass\n",
        )
        pkgs = {p.name: p for p in _packages(tmp_path)}
        top_p = pkgs["top"]
        assert top_p.ce >= 1
        assert top_p.ca == 0
        assert top_p.zone == "uselessness"


# ---------------------------------------------------------------------------
# Distance formula sanity
# ---------------------------------------------------------------------------


class TestDistance:
    def test_distance_is_abs_a_plus_i_minus_one(self, tmp_path: Path):
        # Construct a package with known (I, A) and verify D' formula.
        leaf = tmp_path / "leaf"
        leaf.mkdir()
        (leaf / "__init__.py").write_text("class C:\n    pass\n")
        caller = tmp_path / "caller"
        caller.mkdir()
        (caller / "__init__.py").write_text("from leaf import C\n")
        pkgs = {p.name: p for p in _packages(tmp_path)}
        leaf_p = pkgs["leaf"]
        if leaf_p.instability is not None and leaf_p.abstractness is not None:
            expected = abs(leaf_p.abstractness + leaf_p.instability - 1.0)
            assert abs(leaf_p.distance - expected) < 1e-9  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Cross-package coupling aggregation
# ---------------------------------------------------------------------------


class TestCoupling:
    def test_intra_package_edges_dont_count(self, tmp_path: Path):
        # ``pkg.a`` imports ``pkg.b`` — same package, so the edge
        # contributes nothing to either Ca or Ce.
        pkg = tmp_path / "pkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "a.py").write_text("from pkg.b import x\n")
        (pkg / "b.py").write_text("x = 1\n")
        pkgs = _packages(tmp_path)
        assert len(pkgs) == 1
        p = pkgs[0]
        assert p.ca == 0
        assert p.ce == 0
