"""hotspots — churn x complexity priority signal as an observation.

The metric is git-dependent (covered in the metric tests); here we unit-test the
rule's behaviour: it emits an observation only for the ``hotspot`` quadrant, with the
right claim-free shape, and is silent off-git.
"""
from __future__ import annotations

from pathlib import Path

from slop.finding import Action, Disposition, Severity
from slop.metrics.structural.records import Hotspot
from slop.rules import RULE_REGISTRY
from slop.rules.hotspots import HotspotsRule
from slop.scope import scan_corpus
from slop.scope.identity import ScopeKind


class _FakeView:
    def __init__(self, rows):
        self._rows = rows

    def hotspots(self, *, since):
        return self._rows


def test_default_config():
    rc = HotspotsRule.default_config()
    assert HotspotsRule.altitudes == frozenset({ScopeKind.CORPUS})
    assert rc.param("since") == "14 days ago"


def test_registered():
    assert any(isinstance(r, HotspotsRule) for r in RULE_REGISTRY)


def test_emits_only_hotspot_quadrant(tmp_path: Path, monkeypatch):
    (tmp_path / "m.py").write_text("x = 1\n")
    corpus = scan_corpus(tmp_path, config=None)
    rows = [
        Hotspot(path="hot.py", churn=200, complexity=50, quadrant="hotspot"),
        Hotspot(path="calm.py", churn=1, complexity=1, quadrant="calm"),
        Hotspot(path="cx.py", churn=1, complexity=99, quadrant="stable_complex"),
    ]
    monkeypatch.setattr(
        "slop.rules.hotspots.Structure",
        type("S", (), {"over": staticmethod(lambda c: _FakeView(rows))}),
    )
    findings = list(HotspotsRule().check(corpus, HotspotsRule.default_config()))
    assert len(findings) == 1
    f = findings[0]
    assert f.disposition is Disposition.OBSERVATION
    assert f.action is Action.INVESTIGATE
    assert f.severity is Severity.INFO
    assert f.evidence.kind == "hotspot"
    assert f.evidence.data["path"] == "hot.py"
    assert "hot.py" in f.message


def test_silent_off_git(tmp_path: Path):
    # tmp_path is not a git repo → the metric returns [], the rule yields nothing.
    (tmp_path / "m.py").write_text("def f():\n    return 1\n")
    corpus = scan_corpus(tmp_path, config=None)
    assert list(HotspotsRule().check(corpus, HotspotsRule.default_config())) == []
