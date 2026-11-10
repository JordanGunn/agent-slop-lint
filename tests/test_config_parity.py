"""Config discovery: upward walk, pyproject[tool.slop], and the schema."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from slop import cli
from slop.config import AnalysisConfig
from slop.dispatch import Dispatcher
from slop.rules import RULE_REGISTRY
from slop.scope import scan_corpus

# a function tangled enough to trip complexity.cyclomatic
TANGLED = "def f(a, b):\n" + "".join(f"    if a == {i}: b += 1\n" for i in range(15)) + "    return b\n"


def _cyclomatic_count(root: Path) -> int:
    cfg = AnalysisConfig.load(root, RULE_REGISTRY)
    report = Dispatcher(RULE_REGISTRY, cfg).run(scan_corpus(root, cfg))
    return sum(1 for v in report.violations if v.rule == "complexity.cyclomatic")


def test_discovery_walks_up_to_pyproject(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text(
        '[tool.slop.rules."complexity.cyclomatic".thresholds]\ncallable = 100\n')
    sub = tmp_path / "pkg"
    sub.mkdir()
    (sub / "m.py").write_text(TANGLED)
    # discovered by walking up from sub: the raised threshold applies, so no violation
    cfg = AnalysisConfig.load(sub, RULE_REGISTRY)
    assert cfg.for_rule("complexity.cyclomatic").thresholds == {"callable": 100}
    assert _cyclomatic_count(sub) == 0


def test_pyproject_tool_slop_rejects_unknown_keys(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text('[tool.slop.ignore]\nfunctions = ["f"]\n')
    with pytest.raises(ValueError, match="unknown key"):
        AnalysisConfig.load(tmp_path, RULE_REGISTRY)


def test_dot_slop_toml_takes_precedence_over_pyproject(tmp_path: Path):
    (tmp_path / ".slop.toml").write_text("")
    (tmp_path / "pyproject.toml").write_text(
        '[tool.slop.rules."complexity.cyclomatic"]\nenabled = false\n')
    (tmp_path / "m.py").write_text(TANGLED)
    assert _cyclomatic_count(tmp_path) == 1   # the empty .slop.toml won; the rule stays on


def test_pyproject_without_tool_slop_is_skipped(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text("[tool.other]\nx = 1\n")
    (tmp_path / "m.py").write_text(TANGLED)
    assert _cyclomatic_count(tmp_path) == 1


def test_schema_generated_from_registry(capsys):
    rc = cli.schema_cmd("json")
    data = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert data["version"] == "v2"
    assert "ignore" not in data
    assert {"exclude", "languages", "rules"} <= set(data)
    assert {r["name"] for r in data["rules"]} == {r.name for r in RULE_REGISTRY}
    cyclo = next(r for r in data["rules"] if r["name"] == "complexity.cyclomatic")
    assert cyclo["thresholds"] == {"callable": 10} and cyclo["altitudes"] == ["callable"]
    assert all("severity" not in r for r in data["rules"])
