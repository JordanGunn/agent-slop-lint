"""lexical.imposters — missing-class observation over first-parameter clusters."""
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


def test_missing_class_emits_observation(tmp_path: Path):
    # An inferred receiver cluster is evidence, not a directive verdict (disposition
    # policy): the missing-class signal surfaces as a claim-free observation.
    (tmp_path / "a.py").write_text(RECEIVER)
    corpus = scan_corpus(tmp_path, config=None)
    findings = list(ImpostersRule().check(corpus, ImpostersRule.default_config()))
    assert len(findings) == 1
    f = findings[0]
    assert f.disposition is Disposition.OBSERVATION
    assert f.action is Action.INVESTIGATE
    assert f.severity is Severity.INFO
    assert f.evidence.kind == "receiver-cluster"
    assert f.metadata["parameter"] == "cfg"
    assert f.metadata["profile"] == "missing_class"


# Same receiver cluster (cfg), but the three bodies are IDENTICAL — so they are also a
# Type-2 clone family. The structural signal corroborates the inferred cluster.
CORROBORATED = '''\
def alpha_cfg(cfg, x):
    a = cfg.value
    b = a + 1
    c = b * 2
    d = c - 3
    cfg.result = d
    return d + a + b + c

def beta_cfg(cfg, y):
    a = cfg.value
    b = a + 1
    c = b * 2
    d = c - 3
    cfg.result = d
    return d + a + b + c

def gamma_cfg(cfg, z):
    a = cfg.value
    b = a + 1
    c = b * 2
    d = c - 3
    cfg.result = d
    return d + a + b + c
'''


def test_corroborated_cluster_promotes_to_review(tmp_path: Path):
    # A receiver cluster whose members are ALSO Type-2 clones is corroborated by an
    # independent structural signal — it earns a REVIEW verdict, not a bare observation.
    (tmp_path / "a.py").write_text(CORROBORATED)
    corpus = scan_corpus(tmp_path, config=None)
    findings = list(ImpostersRule().check(corpus, ImpostersRule.default_config()))
    assert len(findings) == 1
    f = findings[0]
    assert f.disposition is Disposition.VERDICT
    assert f.action is Action.REVIEW
    assert f.severity is Severity.WARNING
    assert f.metadata["corroborated"] is True


def test_below_min_cluster_silent(tmp_path: Path):
    (tmp_path / "a.py").write_text(RECEIVER)
    corpus = scan_corpus(tmp_path, config=None)
    cfg = ImpostersRule.default_config()
    cfg.params["min_cluster"] = 4
    assert list(ImpostersRule().check(corpus, cfg)) == []
