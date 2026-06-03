"""lexical.slackers — real cluster whose member names refuse to align (verdict)."""
from __future__ import annotations

from pathlib import Path

from slop.finding import Action, Disposition, Severity
from slop.rules import RULE_REGISTRY
from slop.rules.slackers import SlackersRule
from slop.scope import scan_corpus
from slop.scope.identity import ScopeKind

# missing_class cluster (cfg receiver) with disjoint-stem names → 0% template coverage.
MISALIGNED = '''\
def fetch_user_record(cfg):
    cfg.a = 1
    return cfg.b

def compute_billing_total(cfg):
    cfg.c = 2
    return cfg.b

def render_dashboard_widget(cfg):
    cfg.d = 3
    return cfg.b
'''

# Same receiver cluster, but names share a template (verb_cfg) → high coverage.
ALIGNED = '''\
def load_cfg(cfg):
    cfg.a = 1
    return cfg.b

def save_cfg(cfg):
    cfg.c = 2
    return cfg.b

def drop_cfg(cfg):
    cfg.d = 3
    return cfg.b
'''


def test_default_config():
    rc = SlackersRule.default_config()
    assert SlackersRule.altitudes == frozenset({ScopeKind.CORPUS})
    assert rc.param("max_coverage") == 0.30


def test_registered():
    assert any(isinstance(r, SlackersRule) for r in RULE_REGISTRY)


def test_fires_when_names_dont_align(tmp_path: Path):
    (tmp_path / "a.py").write_text(MISALIGNED)
    corpus = scan_corpus(tmp_path, config=None)
    findings = list(SlackersRule().check(corpus, SlackersRule.default_config()))
    assert len(findings) == 1
    f = findings[0]
    assert f.disposition is Disposition.VERDICT
    assert f.action is Action.RENAME_BY_TEMPLATE
    assert f.severity is Severity.WARNING
    assert f.metadata["parameter"] == "cfg"


def test_silent_when_names_align(tmp_path: Path):
    (tmp_path / "a.py").write_text(ALIGNED)
    corpus = scan_corpus(tmp_path, config=None)
    assert list(SlackersRule().check(corpus, SlackersRule.default_config())) == []
