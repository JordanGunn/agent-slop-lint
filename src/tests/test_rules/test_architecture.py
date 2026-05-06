"""Tests for slop packages rule (Robert C. Martin D').

Every language slop supports has `packages` coverage. These tests verify that
robert_kernel produces sensible abstract/concrete counts for each language.
Fixtures are deliberately small — one abstract type (interface/trait/ABC),
one abstract class where the language has one, and one or two concrete types.
"""

from __future__ import annotations

from pathlib import Path

from slop._structural.robert import robert_kernel
from slop.models import RuleConfig, SlopConfig
from slop.rules.architecture import run_distance


# ---------------------------------------------------------------------------
# Rule-level behavior
# ---------------------------------------------------------------------------


def test_packages_pass_when_clean(tmp_path: Path):
    (tmp_path / "main.py").write_text("def main():\n    pass\n")
    rc = RuleConfig(enabled=True, severity="warning", params={
        "max_distance": 0.7, "fail_on_zone": ["pain"], "languages": ["python"],
    })
    result = run_distance(tmp_path, rc, SlopConfig(root=str(tmp_path)))
    assert result.status in ("pass", "skip")


def test_packages_skip_when_no_supported_languages(tmp_path: Path):
    # Kotlin is not in robert's supported set; should skip cleanly.
    (tmp_path / "Main.kt").write_text("fun main() {}\n")
    rc = RuleConfig(enabled=True, severity="warning", params={
        "max_distance": 0.7, "fail_on_zone": ["pain"], "languages": ["kotlin"],
    })
    result = run_distance(tmp_path, rc, SlopConfig(root=str(tmp_path), languages=["kotlin"]))
    assert result.status == "skip"


# ---------------------------------------------------------------------------
# Per-language kernel behavior
#
# Each test drops a single-package fixture into tmp_path and asserts that
# robert_kernel counts the expected abstract / concrete types. We don't
# assert distance directly because a single-package project has zero coupling
# (ca=ce=0) and instability is None, which makes distance None by definition.
# What we care about here is whether na and nc come out right.
# ---------------------------------------------------------------------------


def _only_package(result, language: str):
    assert result.language == language
    assert result.errors == []
    assert len(result.packages) == 1
    return result.packages[0]


def test_robert_java_counts_interface_abstract_class_and_concrete(tmp_path: Path):
    pkg = tmp_path / "com" / "example"
    pkg.mkdir(parents=True)
    (pkg / "IShape.java").write_text("package com.example;\npublic interface IShape { double area(); }\n")
    (pkg / "AbstractShape.java").write_text(
        "package com.example;\npublic abstract class AbstractShape implements IShape {}\n"
    )
    (pkg / "Circle.java").write_text(
        "package com.example;\npublic class Circle extends AbstractShape { public double area() { return 0; } }\n"
    )
    (pkg / "Point.java").write_text("package com.example;\npublic record Point(int x, int y) {}\n")
    result = robert_kernel(tmp_path, language="java")
    p = _only_package(result, "java")
    assert p.na == 2       # IShape, AbstractShape
    assert p.nc == 2       # Circle, Point


def test_robert_csharp_counts_interface_abstract_class_struct_and_record(tmp_path: Path):
    pkg = tmp_path
    (pkg / "IShape.cs").write_text("namespace X { public interface IShape { double Area(); } }\n")
    (pkg / "Shape.cs").write_text("namespace X { public abstract class Shape : IShape { public abstract double Area(); } }\n")
    (pkg / "Circle.cs").write_text("namespace X { public class Circle : Shape { public override double Area() => 0; } }\n")
    (pkg / "Point.cs").write_text("namespace X { public struct Point { public int X; public int Y; } }\n")
    (pkg / "Person.cs").write_text("namespace X { public record Person(string Name, int Age); }\n")
    result = robert_kernel(tmp_path, language="c_sharp")
    p = _only_package(result, "c_sharp")
    assert p.na == 2       # IShape, Shape
    assert p.nc == 3       # Circle, Point, Person


def test_robert_typescript_counts_interface_abstract_class_and_concrete(tmp_path: Path):
    pkg = tmp_path
    (pkg / "shape.ts").write_text(
        "export interface Shape { area(): number; }\n"
        "export abstract class BaseShape implements Shape { abstract area(): number; }\n"
        "export class Circle extends BaseShape { area() { return 0; } }\n"
    )
    result = robert_kernel(tmp_path, language="typescript")
    p = _only_package(result, "typescript")
    assert p.na == 2       # Shape, BaseShape
    assert p.nc == 1       # Circle


def test_robert_javascript_counts_all_classes_as_concrete(tmp_path: Path):
    pkg = tmp_path
    (pkg / "shapes.js").write_text(
        "export class Circle {}\n"
        "export class Square {}\n"
    )
    result = robert_kernel(tmp_path, language="javascript")
    p = _only_package(result, "javascript")
    assert p.na == 0       # JS has no abstract concept; always 0
    assert p.nc == 2


def test_robert_rust_counts_trait_struct_enum(tmp_path: Path):
    pkg = tmp_path
    (pkg / "lib.rs").write_text(
        "pub trait Shape { fn area(&self) -> f64; }\n"
        "pub struct Circle { r: f64 }\n"
        "pub enum Color { Red, Blue }\n"
    )
    result = robert_kernel(tmp_path, language="rust")
    p = _only_package(result, "rust")
    assert p.na == 1       # Shape trait
    assert p.nc == 2       # Circle (struct) + Color (enum)


def test_robert_unsupported_language_returns_error(tmp_path: Path):
    """Use a truly unsupported language (bash) — Ruby is supported as of v1.0.3."""
    (tmp_path / "main.sh").write_text("echo hello\n")
    result = robert_kernel(tmp_path, language="bash")
    assert result.packages == []
    assert any("Unsupported language" in e for e in result.errors)
