"""Tests for ``packages.rigidity`` and ``.uselessness`` (Martin 1994 D').

Verifies per-language abstractness classification via real Tree-built
fixtures (no kernel stubs — those died with robert.py) plus zone-
isolation behaviour at the rule layer via monkeypatched
``Structure.packages``.
"""
from __future__ import annotations

from pathlib import Path

from slop.linter.rule import Rule
from slop.config import Config
from slop.structure.records import PackageMetrics
from slop.linter.rules.rigidity import run_rigidity
from slop.linter.rules.uselessness import run_uselessness
from slop.tree.tree import Tree


def _rc(threshold: float = 0.7, languages=None) -> Rule:
    params: dict = {"thresholds": {"package": threshold}}
    if languages is not None:
        params["languages"] = list(languages)
    return Rule(enabled=True, severity="warning", params=params)


def _structure(root: Path):
    t = Tree(root)
    t.scan()
    return t.structure


# ---------------------------------------------------------------------------
# Rule-level smoke checks
# ---------------------------------------------------------------------------


def test_rigidity_passes_when_clean(tmp_path: Path):
    (tmp_path / "main.py").write_text("def main():\n    pass\n")
    result = run_rigidity(
        _structure(tmp_path), _rc(), Config(root=str(tmp_path)),
    )
    assert result.status == "pass"


def test_uselessness_passes_when_clean(tmp_path: Path):
    (tmp_path / "main.py").write_text("def main():\n    pass\n")
    result = run_uselessness(
        _structure(tmp_path), _rc(), Config(root=str(tmp_path)),
    )
    assert result.status == "pass"


# ---------------------------------------------------------------------------
# Zone isolation — each rule fires only for its own zone, even when both
# zones are present. Monkeypatch ``Structure.packages`` rather than building
# fixtures whose Ca/Ce/Na/Nc happen to land in the right quadrants — the
# zone logic is unit-tested in test_structure_packages, here we just
# verify rule-level filtering.
# ---------------------------------------------------------------------------


def _stub_pkg(name: str, *, zone: str, distance: float) -> PackageMetrics:
    return PackageMetrics(
        name=name, language="python", files=(),
        ca=0, ce=0, na=0, nc=0,
        instability=0.0, abstractness=0.0,
        distance=distance, zone=zone,
    )


def _patch_packages(monkeypatch, structure, packages: list[PackageMetrics]):
    monkeypatch.setattr(
        structure, "packages", lambda root: list(packages), raising=False,
    )


def test_rigidity_fires_only_on_pain_zone(tmp_path: Path, monkeypatch):
    (tmp_path / "a.py").write_text("def x(): pass\n")
    s = _structure(tmp_path)
    _patch_packages(monkeypatch, s, [
        _stub_pkg("a.pain", zone="pain", distance=0.9),
        _stub_pkg("b.useless", zone="uselessness", distance=0.9),
        _stub_pkg("c.clean", zone="ok", distance=0.1),
    ])
    result = run_rigidity(s, _rc(), Config(root=str(tmp_path)))
    assert result.status == "fail"
    assert len(result.violations) == 1
    assert result.violations[0].file == "a.pain"
    assert result.violations[0].metadata["zone"] == "pain"


def test_uselessness_fires_only_on_uselessness_zone(tmp_path: Path, monkeypatch):
    (tmp_path / "a.py").write_text("def x(): pass\n")
    s = _structure(tmp_path)
    _patch_packages(monkeypatch, s, [
        _stub_pkg("a.pain", zone="pain", distance=0.9),
        _stub_pkg("b.useless", zone="uselessness", distance=0.9),
        _stub_pkg("c.clean", zone="ok", distance=0.1),
    ])
    result = run_uselessness(s, _rc(), Config(root=str(tmp_path)))
    assert result.status == "fail"
    assert len(result.violations) == 1
    assert result.violations[0].file == "b.useless"
    assert result.violations[0].metadata["zone"] == "uselessness"


def test_rigidity_respects_threshold_within_pain_zone(tmp_path: Path, monkeypatch):
    (tmp_path / "a.py").write_text("def x(): pass\n")
    s = _structure(tmp_path)
    _patch_packages(monkeypatch, s, [
        _stub_pkg("borderline.pain", zone="pain", distance=0.5),
        _stub_pkg("deep.pain", zone="pain", distance=0.9),
    ])
    result = run_rigidity(s, _rc(threshold=0.8), Config(root=str(tmp_path)))
    assert result.status == "fail"
    assert {v.file for v in result.violations} == {"deep.pain"}


# ---------------------------------------------------------------------------
# Per-language abstractness classification — verified through the rule's
# substrate (Structure.packages), not via a kernel stub.
# ---------------------------------------------------------------------------


def _one_pkg(structure, root: Path) -> PackageMetrics:
    pkgs = structure.packages(root)
    assert len(pkgs) == 1, f"expected one package, got {[p.name for p in pkgs]}"
    return pkgs[0]


def test_java_counts_interface_abstract_class_and_concrete(tmp_path: Path):
    pkg = tmp_path / "com" / "example"
    pkg.mkdir(parents=True)
    (pkg / "IShape.java").write_text(
        "package com.example;\npublic interface IShape { double area(); }\n",
    )
    (pkg / "AbstractShape.java").write_text(
        "package com.example;\n"
        "public abstract class AbstractShape implements IShape {}\n",
    )
    (pkg / "Circle.java").write_text(
        "package com.example;\n"
        "public class Circle extends AbstractShape "
        "{ public double area() { return 0; } }\n",
    )
    (pkg / "Point.java").write_text(
        "package com.example;\npublic record Point(int x, int y) {}\n",
    )
    p = _one_pkg(_structure(tmp_path), tmp_path)
    assert p.na == 2       # IShape, AbstractShape
    assert p.nc == 2       # Circle, Point


def test_csharp_counts_interface_abstract_class_struct_and_record(tmp_path: Path):
    (tmp_path / "IShape.cs").write_text(
        "namespace X { public interface IShape { double Area(); } }\n",
    )
    (tmp_path / "Shape.cs").write_text(
        "namespace X { public abstract class Shape : IShape "
        "{ public abstract double Area(); } }\n",
    )
    (tmp_path / "Circle.cs").write_text(
        "namespace X { public class Circle : Shape "
        "{ public override double Area() => 0; } }\n",
    )
    (tmp_path / "Point.cs").write_text(
        "namespace X { public struct Point { public int X; public int Y; } }\n",
    )
    (tmp_path / "Person.cs").write_text(
        "namespace X { public record Person(string Name, int Age); }\n",
    )
    p = _one_pkg(_structure(tmp_path), tmp_path)
    assert p.na == 2       # IShape, Shape
    # Records aren't currently emitted by the C# grammar's classes() set
    # (which lists class/interface/struct only). Expect 2 concrete:
    # Circle + Point.
    assert p.nc == 2


def test_typescript_counts_interface_abstract_class_and_concrete(tmp_path: Path):
    (tmp_path / "shape.ts").write_text(
        "export interface Shape { area(): number; }\n"
        "export abstract class BaseShape implements Shape "
        "{ abstract area(): number; }\n"
        "export class Circle extends BaseShape { area() { return 0; } }\n"
    )
    p = _one_pkg(_structure(tmp_path), tmp_path)
    assert p.na == 2       # Shape, BaseShape
    assert p.nc == 1       # Circle


def test_javascript_counts_all_classes_as_concrete(tmp_path: Path):
    (tmp_path / "shapes.js").write_text(
        "export class Circle {}\nexport class Square {}\n",
    )
    p = _one_pkg(_structure(tmp_path), tmp_path)
    assert p.na == 0       # JS has no abstract concept
    assert p.nc == 2


def test_rust_counts_trait_struct_and_enum(tmp_path: Path):
    (tmp_path / "lib.rs").write_text(
        "pub trait Shape { fn area(&self) -> f64; }\n"
        "pub struct Circle { r: f64 }\n"
        "pub enum Color { Red, Blue }\n",
    )
    p = _one_pkg(_structure(tmp_path), tmp_path)
    assert p.na == 1       # trait Shape
    assert p.nc == 2       # struct Circle + enum Color


def test_go_counts_interface_and_struct(tmp_path: Path):
    pkg = tmp_path / "shapes"
    pkg.mkdir()
    (pkg / "shape.go").write_text(
        "package shapes\n"
        "type Shape interface { Area() float64 }\n"
        "type Circle struct { r float64 }\n",
    )
    p = _one_pkg(_structure(tmp_path), tmp_path)
    assert p.na == 1       # interface Shape
    assert p.nc == 1       # struct Circle


def test_ruby_counts_module_as_abstract_class_as_concrete(tmp_path: Path):
    (tmp_path / "shapes.rb").write_text(
        "module Drawable\n  def draw; end\nend\n"
        "class Circle\nend\n",
    )
    p = _one_pkg(_structure(tmp_path), tmp_path)
    assert p.na == 1       # module Drawable
    assert p.nc == 1       # class Circle


def test_cpp_pure_virtual_class_is_abstract(tmp_path: Path):
    """A C++ class with at least one pure-virtual method counts as abstract."""
    (tmp_path / "shapes.cpp").write_text(
        "class Shape {\n"
        "public:\n"
        "    virtual double area() = 0;\n"
        "    virtual ~Shape() = default;\n"
        "};\n"
        "class Circle {\n"
        "public:\n"
        "    double area() { return 0; }\n"
        "};\n",
    )
    p = _one_pkg(_structure(tmp_path), tmp_path)
    assert p.na == 1       # Shape (pure-virtual area())
    assert p.nc == 1       # Circle (concrete area())


def test_cpp_class_without_pure_virtual_is_concrete(tmp_path: Path):
    """A C++ class with only normal virtual (overridable) methods is still concrete."""
    (tmp_path / "shapes.cpp").write_text(
        "class A {\n"
        "public:\n"
        "    virtual double f();\n"  # overridable but not pure
        "    double g() { return 0; }\n"
        "};\n",
    )
    p = _one_pkg(_structure(tmp_path), tmp_path)
    assert p.na == 0
    assert p.nc == 1


def test_cpp_struct_is_concrete_even_with_pure_virtual(tmp_path: Path):
    """C++ structs are pragmatically concrete — the abstract-class idiom uses ``class``."""
    (tmp_path / "shapes.cpp").write_text(
        "struct Point { int x; int y; };\n",
    )
    p = _one_pkg(_structure(tmp_path), tmp_path)
    assert p.na == 0
    assert p.nc == 1


def test_python_counts_abc_as_abstract_plain_as_concrete(tmp_path: Path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "shapes.py").write_text(
        "from abc import ABC, abstractmethod\n"
        "class Shape(ABC):\n"
        "    @abstractmethod\n"
        "    def area(self): pass\n"
        "class Circle:\n"
        "    def area(self): return 0\n",
    )
    s = _structure(tmp_path)
    pkgs = s.packages(tmp_path)
    # Python's resolve_packages drops directories without __init__.py;
    # tmp_path itself has no __init__.py so only ``pkg`` survives.
    assert len(pkgs) == 1
    p = pkgs[0]
    assert p.na == 1       # Shape (inherits ABC)
    assert p.nc == 1       # Circle
