"""import-cycle: one violation per import cycle (ADP, Martin 2002)."""
from __future__ import annotations

from pathlib import Path

from slop.rules import RULE_REGISTRY
from slop.rules.dependency_cycles import DependencyCyclesRule
from slop.scope import scan_corpus
from slop.scope.identity import ScopeKind


def _corpus(tmp_path: Path, cyclic: bool):
    (tmp_path / "a.py").write_text("import b\n")
    (tmp_path / "b.py").write_text("import a\n" if cyclic else "x = 1\n")
    return scan_corpus(tmp_path, config=None)


def _check(corpus):
    return list(DependencyCyclesRule().check(corpus, DependencyCyclesRule.default_config()))


def test_default_config_is_corpus_altitude_without_threshold():
    rc = DependencyCyclesRule.default_config()
    assert DependencyCyclesRule.altitudes == frozenset({ScopeKind.CORPUS})
    assert rc.options == {} and rc.enabled


def test_registered():
    assert any(isinstance(r, DependencyCyclesRule) for r in RULE_REGISTRY)


def test_fires_on_cycle_at_first_module_by_path(tmp_path: Path):
    [v] = _check(_corpus(tmp_path, cyclic=True))
    assert v.rule == "import-cycle"
    assert v.path == str(tmp_path / "a.py")
    assert (v.line, v.column) == (1, 1)
    assert v.value == 2 and v.threshold == 0
    assert "a.py" in v.message and "b.py" in v.message


def test_one_violation_per_cycle(tmp_path: Path):
    for name, dep in (("a", "b"), ("b", "a"), ("c", "d"), ("d", "c")):
        (tmp_path / f"{name}.py").write_text(f"import {dep}\n")
    vs = _check(scan_corpus(tmp_path, config=None))
    assert sorted(Path(v.path).name for v in vs) == ["a.py", "c.py"]


def test_same_named_modules_are_both_named_by_path(tmp_path: Path):
    # Two `x` modules in different packages: the message must name both by path and the
    # violation sits at the first by path, not at whichever `x` a name lookup found last.
    for pkg, other in (("a", "b"), ("b", "a")):
        (tmp_path / pkg).mkdir()
        (tmp_path / pkg / "__init__.py").write_text("")
        (tmp_path / pkg / "x.py").write_text(f"from {other}.x import f\n")
    [v] = _check(scan_corpus(tmp_path, config=None))
    assert "a/x.py → b/x.py → a/x.py" in v.message
    assert v.path == str(tmp_path / "a" / "x.py")
    assert v.value == 2


def test_silent_without_cycle(tmp_path: Path):
    assert _check(_corpus(tmp_path, cyclic=False)) == []
