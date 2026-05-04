"""Tests for slop class rules (CBO, DIT, NOC)."""

from __future__ import annotations

from pathlib import Path

from slop.models import RuleConfig, SlopConfig
from slop.rules.class_metrics import run_coupling, run_inheritance_children, run_inheritance_depth


def _default_config() -> SlopConfig:
    return SlopConfig(rules={})


def test_coupling_violation_above_threshold(tmp_path: Path):
    # Create many classes, one class referencing all of them
    classes = [f"class Dep{i}:\n    pass" for i in range(10)]
    refs = ", ".join(f"d{i}: Dep{i}" for i in range(10))
    classes.append(f"class Hub:\n    def m(self, {refs}):\n        pass")
    (tmp_path / "test.py").write_text("\n\n".join(classes))
    rc = RuleConfig(enabled=True, severity="error", params={"threshold": 8})
    result = run_coupling(tmp_path, rc, _default_config())
    assert result.status == "fail"
    hub_violations = [v for v in result.violations if v.symbol == "Hub"]
    assert len(hub_violations) == 1
    assert hub_violations[0].value is not None and hub_violations[0].value > 8


def test_coupling_pass_below_threshold(tmp_path: Path):
    (tmp_path / "test.py").write_text("class Simple:\n    def method(self):\n        pass\n")
    rc = RuleConfig(enabled=True, severity="error", params={"threshold": 8})
    result = run_coupling(tmp_path, rc, _default_config())
    assert result.status == "pass"


def test_inheritance_depth_violation(tmp_path: Path):
    (tmp_path / "test.py").write_text(
        "class A:\n    pass\n\n"
        "class B(A):\n    pass\n\n"
        "class C(B):\n    pass\n\n"
        "class D(C):\n    pass\n\n"
        "class E(D):\n    pass\n"
    )
    rc = RuleConfig(enabled=True, severity="error", params={"threshold": 3})
    result = run_inheritance_depth(tmp_path, rc, _default_config())
    assert result.status == "fail"
    # D has DIT=3, E has DIT=4 — both exceed threshold of 3
    deep = [v for v in result.violations if v.value is not None and v.value > 3]
    assert len(deep) >= 1


def test_inheritance_children_violation(tmp_path: Path):
    source = "class Base:\n    pass\n\n"
    source += "\n\n".join(f"class Child{i}(Base):\n    pass" for i in range(12))
    (tmp_path / "test.py").write_text(source)
    rc = RuleConfig(enabled=True, severity="error", params={"threshold": 10})
    result = run_inheritance_children(tmp_path, rc, _default_config())
    assert result.status == "fail"
    base_violations = [v for v in result.violations if v.symbol == "Base"]
    assert len(base_violations) == 1
    assert base_violations[0].value == 12
