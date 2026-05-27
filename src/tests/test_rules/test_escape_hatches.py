"""Tests for ``types.escape_hatches`` (annotation density)."""
from __future__ import annotations

from pathlib import Path

from slop.linter.rule import Rule
from slop.config import Config
from slop.linter.rules.escape_hatches import run_escape_hatches
from slop.tree.tree import Tree


def _structure(root: Path):
    t = Tree(root)
    t.scan()
    return t.structure


def _rc(**overrides) -> Rule:
    threshold = overrides.pop("threshold", 0.30)
    params: dict = {
        "thresholds": {"module": threshold},
        "min_annotations": 2,
    }
    params.update(overrides)
    return Rule(enabled=True, severity="warning", params=params)


def _sc(tmp_path: Path) -> Config:
    return Config(root=str(tmp_path))


_ANY_HEAVY = """\
from typing import Any, List, Dict

def process(data: Any) -> Any:
    items: List[Any] = list(data)
    return data

def transform(x: int) -> int:
    return x * 2
"""

_ANY_CLEAN = """\
from typing import List, Dict

def process(data: List[int]) -> Dict[str, int]:
    for item in data:
        yield item
"""


# ---------------------------------------------------------------------------
# Structure.type_annotations — view-method unit tests
# ---------------------------------------------------------------------------


def test_view_extracts_python_annotations(tmp_path: Path):
    (tmp_path / "a.py").write_text(_ANY_HEAVY)
    anns = list(_structure(tmp_path).type_annotations())
    texts = [a.text for a in anns]
    assert "Any" in texts
    assert "int" in texts


def test_view_classifies_python_any_as_escape(tmp_path: Path):
    (tmp_path / "a.py").write_text(_ANY_HEAVY)
    anns = list(_structure(tmp_path).type_annotations())
    any_count = sum(1 for a in anns if a.is_escape)
    non_any = sum(1 for a in anns if not a.is_escape)
    assert any_count >= 3  # data: Any, -> Any, items: List[Any] (counts via token check)
    assert non_any >= 2    # x: int, -> int


def test_view_clean_file_zero_escapes(tmp_path: Path):
    (tmp_path / "a.py").write_text(_ANY_CLEAN)
    anns = list(_structure(tmp_path).type_annotations())
    assert all(not a.is_escape for a in anns)


def test_view_typescript_any(tmp_path: Path):
    (tmp_path / "a.ts").write_text(
        "function f(x: any, y: number): any { return x; }\n",
    )
    anns = list(_structure(tmp_path).type_annotations())
    escapes = [a.text for a in anns if a.is_escape]
    assert escapes == ["any", "any"] or set(escapes) == {"any"}


def test_view_go_interface_empty(tmp_path: Path):
    (tmp_path / "a.go").write_text(
        'package x\nfunc f(x any, y int) interface{} { return nil }\n',
    )
    anns = list(_structure(tmp_path).type_annotations())
    escapes = {a.text for a in anns if a.is_escape}
    assert "any" in escapes
    assert "interface{}" in escapes


def test_view_java_object(tmp_path: Path):
    (tmp_path / "A.java").write_text(
        "class X { public Object f(Object x, int y) { return null; } }\n",
    )
    anns = list(_structure(tmp_path).type_annotations())
    escapes = [a.text for a in anns if a.is_escape]
    assert escapes.count("Object") == 2  # return + param


def test_view_csharp_object_and_dynamic(tmp_path: Path):
    (tmp_path / "A.cs").write_text(
        "class X { public object f(object x, int y) { return null; }"
        " public dynamic g() => null; }\n",
    )
    anns = list(_structure(tmp_path).type_annotations())
    escapes = {a.text for a in anns if a.is_escape}
    assert "object" in escapes
    assert "dynamic" in escapes


def test_view_rust_dyn_any(tmp_path: Path):
    (tmp_path / "a.rs").write_text(
        "fn f(x: i32, y: Box<dyn std::any::Any>) -> Box<dyn std::any::Any> "
        "{ unimplemented!() }\n",
    )
    anns = list(_structure(tmp_path).type_annotations())
    escapes = [a.text for a in anns if a.is_escape]
    assert any("dyn" in t for t in escapes)


def test_view_julia_any(tmp_path: Path):
    (tmp_path / "a.jl").write_text(
        "function f(x::Any, y::Int)::Any\n  return x\nend\n",
    )
    anns = list(_structure(tmp_path).type_annotations())
    escapes = [a.text for a in anns if a.is_escape]
    assert escapes.count("Any") >= 2


# ---------------------------------------------------------------------------
# Rule wrapper tests
# ---------------------------------------------------------------------------


def test_rule_pass_clean_file(tmp_path: Path):
    (tmp_path / "a.py").write_text(_ANY_CLEAN)
    result = run_escape_hatches(_structure(tmp_path), _rc(threshold=0.30), _sc(tmp_path))
    assert result.status == "pass"
    assert result.violations == []


def test_rule_fail_heavy_any(tmp_path: Path):
    (tmp_path / "a.py").write_text(_ANY_HEAVY)
    result = run_escape_hatches(
        _structure(tmp_path),
        _rc(threshold=0.10, min_annotations=2),
        _sc(tmp_path),
    )
    assert result.status == "fail"
    assert len(result.violations) >= 1
    v = result.violations[0]
    assert v.rule == "escape_hatches"
    assert v.severity == "warning"
    assert v.value > 0.10


def test_rule_min_annotations_skips_small_files(tmp_path: Path):
    """Files with fewer annotations than min_annotations should be skipped."""
    (tmp_path / "a.py").write_text("from typing import Any\ndef f(x: Any): return x\n")
    result = run_escape_hatches(
        _structure(tmp_path),
        _rc(threshold=0.0, min_annotations=20),
        _sc(tmp_path),
    )
    assert result.status == "pass"


def test_rule_violation_metadata_keys(tmp_path: Path):
    (tmp_path / "a.py").write_text(_ANY_HEAVY)
    result = run_escape_hatches(
        _structure(tmp_path),
        _rc(threshold=0.0, min_annotations=1),
        _sc(tmp_path),
    )
    if result.violations:
        v = result.violations[0]
        for key in ("language", "escape_count", "total_count", "density"):
            assert key in v.metadata, f"missing key: {key}"


def test_rule_summary_keys(tmp_path: Path):
    (tmp_path / "a.py").write_text(_ANY_CLEAN)
    result = run_escape_hatches(_structure(tmp_path), _rc(), _sc(tmp_path))
    for key in ("files_scanned", "violations", "threshold"):
        assert key in result.summary, f"missing key: {key}"
