"""structure.runts — single-module package with trivial init, FLATTEN_PACKAGE verdict."""
from __future__ import annotations

from pathlib import Path

from slop.finding import Action, Disposition, Severity
from slop.rules import RULE_REGISTRY
from slop.rules.runts import RuntsRule
from slop.scope import scan_corpus
from slop.scope.identity import ScopeKind


def _packages(tmp_path: Path) -> dict:
    return {p.name: p for p in scan_corpus(tmp_path, config=None).realms()[0].packages()}


def test_default_config():
    rc = RuntsRule.default_config()
    assert RuntsRule.altitudes == frozenset({ScopeKind.PACKAGE})
    assert rc.severity is Severity.WARNING


def test_registered():
    assert any(isinstance(r, RuntsRule) for r in RULE_REGISTRY)


def test_fires_on_runt(tmp_path: Path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("")
    (tmp_path / "pkg" / "solo.py").write_text("def f():\n    return 1\n")
    pkg = _packages(tmp_path)["pkg"]
    findings = list(RuntsRule().check(pkg, RuntsRule.default_config()))
    assert len(findings) == 1
    f = findings[0]
    assert f.disposition is Disposition.VERDICT
    assert f.action is Action.FLATTEN_PACKAGE
    assert f.severity is Severity.WARNING
    assert f.metadata["module"] == "solo"
    assert "solo" in f.message


def test_silent_on_multi_module_package(tmp_path: Path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("")
    (tmp_path / "pkg" / "a.py").write_text("x = 1\n")
    (tmp_path / "pkg" / "b.py").write_text("y = 1\n")
    pkg = _packages(tmp_path)["pkg"]
    assert list(RuntsRule().check(pkg, RuntsRule.default_config())) == []


def test_silent_when_init_is_substantial(tmp_path: Path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "solo.py").write_text("x = 1\n")
    (tmp_path / "pkg" / "__init__.py").write_text(
        "class Coordinator:\n" + "".join(f"    def m{i}(self): pass\n" for i in range(6))
    )
    pkg = _packages(tmp_path)["pkg"]
    assert list(RuntsRule().check(pkg, RuntsRule.default_config())) == []
