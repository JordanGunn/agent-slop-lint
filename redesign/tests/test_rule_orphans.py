"""orphans — unreferenced top-level symbols as observations (emit-evidence-not-verdict).

Cross-file fixture: lib.exported_widget is imported by app.py (referenced, not an
orphan); lib.untouched_routine is referenced nowhere (an orphan). Python caps
confidence at "medium" (dynamic-dispatch penalty), so the default high floor is
silent and the medium floor surfaces it.
"""
from __future__ import annotations

from pathlib import Path

from slop.config import RuleConfig
from slop.finding import Action, Disposition, Severity
from slop.rules import RULE_REGISTRY
from slop.rules.orphans import OrphansRule
from slop.scope import scan_corpus
from slop.scope.identity import ScopeKind


def _corpus(tmp_path: Path):
    (tmp_path / "lib.py").write_text(
        "def exported_widget():\n    return 1\n\ndef untouched_routine():\n    return 2\n"
    )
    (tmp_path / "app.py").write_text("from lib import exported_widget\n\nx = exported_widget()\n")
    return scan_corpus(tmp_path, config=None)


def test_default_config():
    rc = OrphansRule.default_config()
    assert OrphansRule.altitudes == frozenset({ScopeKind.CORPUS})
    assert rc.param("min_confidence") == "high"


def test_registered():
    assert any(isinstance(r, OrphansRule) for r in RULE_REGISTRY)


def test_emits_observation_for_unreferenced_symbol(tmp_path: Path):
    corpus = _corpus(tmp_path)
    cfg = RuleConfig(name=OrphansRule.name, params={"min_confidence": "medium"})
    findings = list(OrphansRule().check(corpus, cfg))
    assert len(findings) == 1
    f = findings[0]
    assert f.disposition is Disposition.OBSERVATION
    assert f.action is Action.INVESTIGATE      # observation terminal, never a verdict
    assert f.severity is Severity.INFO          # cannot gate the build
    assert f.evidence.kind == "orphan"
    assert f.evidence.data["qualname"] == "lib.untouched_routine"
    assert "untouched_routine" in f.message


def test_referenced_symbol_is_not_an_orphan(tmp_path: Path):
    corpus = _corpus(tmp_path)
    cfg = RuleConfig(name=OrphansRule.name, params={"min_confidence": "medium"})
    qualnames = {f.evidence.data["qualname"] for f in OrphansRule().check(corpus, cfg)}
    assert "lib.exported_widget" not in qualnames


def test_default_high_floor_silent_on_dynamic_language(tmp_path: Path):
    corpus = _corpus(tmp_path)
    # Python orphans cap at "medium"; the default "high" floor surfaces nothing.
    assert list(OrphansRule().check(corpus, OrphansRule.default_config())) == []
