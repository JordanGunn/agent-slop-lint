"""structure.duplication rule — Type-2 clone cluster emission. Corpus altitude."""
from __future__ import annotations

from pathlib import Path

from slop.finding import Action, Disposition, Severity
from slop.rules import RULE_REGISTRY
from slop.rules.duplication import DuplicationRule
from slop.scope import scan_corpus
from slop.scope.identity import ScopeKind

# alpha and beta are structurally identical (same AST leaf-type fingerprint),
# differing only in identifiers — a Type-2 clone pair. gamma is different.
CLONES = '''\
def alpha(values):
    total = 0
    for item in values:
        if item > 0:
            total = total + item
    return total

def beta(numbers):
    acc = 0
    for n in numbers:
        if n > 0:
            acc = acc + n
    return acc

def gamma(text):
    return text.upper()
'''

NO_CLONES = '''\
def solo(values):
    total = 0
    for item in values:
        if item > 0:
            total = total + item
    return total

def other(text):
    return text.upper()
'''


def _corpus(tmp_path: Path, src: str):
    (tmp_path / "m.py").write_text(src)
    return scan_corpus(tmp_path, config=None)


def test_default_config_is_corpus_altitude():
    rc = DuplicationRule.default_config()
    assert rc.param("min_leaf_nodes") == 10
    assert rc.severity is Severity.WARNING
    assert DuplicationRule.altitudes == frozenset({ScopeKind.CORPUS})


def test_registered():
    assert any(isinstance(r, DuplicationRule) for r in RULE_REGISTRY)


def test_emits_verdict_per_clone_cluster(tmp_path: Path):
    corpus = _corpus(tmp_path, CLONES)
    findings = list(DuplicationRule().check(corpus, DuplicationRule.default_config()))
    assert len(findings) == 1
    f = findings[0]
    assert f.disposition is Disposition.VERDICT
    assert f.action is Action.EXTRACT_HELPER
    assert f.value == 2 and f.threshold == 2
    assert "m.alpha" in f.message and "m.beta" in f.message


def test_silent_without_clones(tmp_path: Path):
    corpus = _corpus(tmp_path, NO_CLONES)
    assert list(DuplicationRule().check(corpus, DuplicationRule.default_config())) == []
