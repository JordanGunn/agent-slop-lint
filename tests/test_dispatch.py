"""Dispatcher: runs each enabled rule at its declared altitudes, records what it visited,
orders violations deterministically, and gates the exit code on any violation."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from slop.config import AnalysisConfig, RuleConfig
from slop.dispatch import Dispatcher
from slop.rule import Rule
from slop.rules import RULE_REGISTRY
from slop.rules.cyclomatic import CyclomaticRule
from slop.scope import scan_corpus
from slop.scope.identity import ScopeKind
from slop.violation import Violation

BRANCHY = "def {n}(v):\n    if v:\n        return 1\n    if v > 2:\n        return 2\n    return 3\n"


class _Recorder(Rule):
    """Flags every component it is handed, and remembers which kinds that was."""

    name = "test.recorder"
    description = "records visits"
    altitudes = frozenset({ScopeKind.MODULE, ScopeKind.CLASS})
    seen: list[ScopeKind] = []

    @classmethod
    def default_config(cls) -> RuleConfig:
        return RuleConfig(name=cls.name, thresholds={"module": 0, "class": 0})

    def check(self, component, config):
        type(self).seen.append(component.id.kind)
        yield Violation.at(component, self.name, f"saw {component.qualname}")


def _config(rule_cls: type[Rule], **kw) -> AnalysisConfig:
    return AnalysisConfig({rule_cls.name: replace(rule_cls.default_config(), **kw)})


def _cyclomatic(tmp_path: Path, limit: int = 2):
    cfg = _config(CyclomaticRule, thresholds={"callable": limit})
    return Dispatcher([CyclomaticRule()], cfg).run(scan_corpus(tmp_path, cfg))


def test_a_rule_is_only_called_at_its_declared_altitudes(tmp_path: Path):
    (tmp_path / "m.py").write_text("class A:\n    def f(self):\n        return 1\n")
    _Recorder.seen = []
    cfg = AnalysisConfig({_Recorder.name: _Recorder.default_config()})
    report = Dispatcher([_Recorder()], cfg).run(scan_corpus(tmp_path, cfg))
    assert set(_Recorder.seen) == {ScopeKind.MODULE, ScopeKind.CLASS}
    assert report.visited[_Recorder.name] == len(_Recorder.seen) == 2
    assert not report.zero_visited


def test_a_disabled_rule_is_neither_run_nor_recorded(tmp_path: Path):
    (tmp_path / "m.py").write_text(BRANCHY.format(n="f"))
    cfg = _config(CyclomaticRule, enabled=False, thresholds={"callable": 1})
    report = Dispatcher([CyclomaticRule()], cfg).run(scan_corpus(tmp_path, cfg))
    assert report.violations == [] and report.visited == {} and report.zero_visited == []


def test_a_rule_missing_from_the_config_is_not_run(tmp_path: Path):
    (tmp_path / "m.py").write_text(BRANCHY.format(n="f"))
    report = Dispatcher([CyclomaticRule()], AnalysisConfig({})).run(scan_corpus(tmp_path, None))
    assert report.violations == [] and report.visited == {}


def test_a_rule_that_visited_nothing_is_reported_not_passed_as_clean(tmp_path: Path):
    (tmp_path / "m.py").write_text("x = 1\ny = 2\n")        # no callable for cyclomatic
    report = _cyclomatic(tmp_path)
    assert report.zero_visited == ["complexity.cyclomatic"]
    assert report.visited["complexity.cyclomatic"] == 0
    assert report.exit_code() == 0


def test_visited_counts_every_component_at_the_altitude(tmp_path: Path):
    (tmp_path / "m.py").write_text(BRANCHY.format(n="a") + BRANCHY.format(n="b") + "class C:\n    def m(self):\n        return 1\n")
    report = _cyclomatic(tmp_path)
    assert report.visited["complexity.cyclomatic"] == 3        # a, b, C.m


def test_exit_code_is_one_if_and_only_if_there_is_a_violation(tmp_path: Path):
    (tmp_path / "m.py").write_text(BRANCHY.format(n="f"))    # cyclomatic 3
    assert _cyclomatic(tmp_path, limit=2).exit_code() == 1
    assert _cyclomatic(tmp_path, limit=3).exit_code() == 0   # strictly greater than the limit


def test_violations_are_sorted_by_path_line_column_rule(tmp_path: Path):
    (tmp_path / "b.py").write_text(BRANCHY.format(n="late"))
    (tmp_path / "a.py").write_text(BRANCHY.format(n="first") + "\n" + BRANCHY.format(n="second"))
    report = _cyclomatic(tmp_path)
    got = [(v.path, v.line) for v in report.violations]
    assert got == sorted(got)
    assert [Path(p).name for p, _ in got] == ["a.py", "a.py", "b.py"]
    assert [ln for _, ln in got] == [1, 8, 1]


def test_as_dict_paths_are_relative_to_the_root(tmp_path: Path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("")
    (tmp_path / "pkg" / "m.py").write_text(BRANCHY.format(n="f"))
    doc = _cyclomatic(tmp_path).as_dict()
    assert doc["summary"] == {"violations": 1, "exit_code": 1}
    [v] = doc["violations"]
    assert v["path"] == "pkg/m.py" and (v["line"], v["column"]) == (1, 1)
    assert set(v) == {"rule", "path", "line", "column", "message", "value", "threshold"}
    assert (v["value"], v["threshold"]) == (3, 2)
    assert doc["zero_visited"] == []


def test_the_default_registry_runs_end_to_end_and_flags_a_tangled_function(tmp_path: Path):
    (tmp_path / "m.py").write_text(
        "def f(a, b):\n" + "".join(f"    if a == {i}: b += 1\n" for i in range(15)) + "    return b\n")
    cfg = AnalysisConfig.defaults(RULE_REGISTRY)
    report = Dispatcher(RULE_REGISTRY, cfg).run(scan_corpus(tmp_path, cfg))
    fired = {v.rule for v in report.violations}
    assert "complexity.cyclomatic" in fired
    assert report.exit_code() == 1
    assert "class.cohesion" not in report.visited      # off by default, so never dispatched
