"""lexical.imposters — missing-class verdict over first-parameter clusters."""
from __future__ import annotations

from pathlib import Path

from slop.finding import Action, Disposition, Severity
from slop.rules import RULE_REGISTRY
from slop.rules.imposters import ImpostersRule
from slop.scope import scan_corpus
from slop.scope.identity import ScopeKind

RECEIVER = '''\
def load_cfg(cfg, path):
    cfg.path = path
    return cfg.value

def save_cfg(cfg, dest):
    cfg.dest = dest
    return cfg.value

def reset_cfg(cfg):
    cfg.value = 0
    return cfg.value
'''


def test_default_config():
    rc = ImpostersRule.default_config()
    assert ImpostersRule.altitudes == frozenset({ScopeKind.CORPUS})
    assert rc.param("min_cluster") == 3


def test_registered():
    assert any(isinstance(r, ImpostersRule) for r in RULE_REGISTRY)


def test_missing_class_emits_extract_class(tmp_path: Path):
    (tmp_path / "a.py").write_text(RECEIVER)
    corpus = scan_corpus(tmp_path, config=None)
    findings = list(ImpostersRule().check(corpus, ImpostersRule.default_config()))
    assert len(findings) == 1
    f = findings[0]
    assert f.disposition is Disposition.VERDICT
    assert f.action is Action.EXTRACT_CLASS
    assert f.severity is Severity.WARNING
    assert f.metadata["parameter"] == "cfg"
    assert f.metadata["profile"] == "missing_class"


def test_below_min_cluster_silent(tmp_path: Path):
    (tmp_path / "a.py").write_text(RECEIVER)
    corpus = scan_corpus(tmp_path, config=None)
    cfg = ImpostersRule.default_config()
    cfg.params["min_cluster"] = 4
    assert list(ImpostersRule().check(corpus, cfg)) == []
