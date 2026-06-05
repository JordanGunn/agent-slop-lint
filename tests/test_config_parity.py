"""Config parity — upward-walk discovery, pyproject[tool.slop], scope-keyed ignore."""
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
    return sum(1 for f in report.findings if f.rule == "complexity.cyclomatic")


def test_discovery_walks_up_to_pyproject(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text('[tool.slop]\n[tool.slop.ignore]\nfunctions = ["f"]\n')
    sub = tmp_path / "pkg"
    sub.mkdir()
    (sub / "m.py").write_text(TANGLED)
    # config discovered by walking up from sub → ignore applies
    cfg = AnalysisConfig.load(sub, RULE_REGISTRY)
    assert cfg.ignore == {"functions": frozenset({"f"})}
    assert _cyclomatic_count(sub) == 0


def test_dot_slop_toml_takes_precedence(tmp_path: Path):
    (tmp_path / ".slop.toml").write_text("")  # empty → no ignore
    (tmp_path / "m.py").write_text(TANGLED)
    assert _cyclomatic_count(tmp_path) == 1   # fires, nothing ignored


def test_pyproject_without_tool_slop_is_skipped(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text("[tool.other]\nx = 1\n")
    (tmp_path / "m.py").write_text(TANGLED)
    assert _cyclomatic_count(tmp_path) == 1


def test_unknown_ignore_scope_raises(tmp_path: Path):
    (tmp_path / ".slop.toml").write_text('[ignore]\nany = ["x"]\n')
    with pytest.raises(ValueError):
        AnalysisConfig.load(tmp_path, RULE_REGISTRY)


def test_schema_generated_from_registry(capsys):
    rc = cli.schema_cmd("json")
    out = capsys.readouterr().out
    assert rc == 0
    data = json.loads(out)
    assert data["version"] == "v1"
    assert set(data["ignore"]) == {"functions", "classes", "modules", "packages"}
    names = {r["name"] for r in data["rules"]}
    assert "complexity.cyclomatic" in names and len(names) == len(RULE_REGISTRY)
