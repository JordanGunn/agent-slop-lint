"""lexical.sprawl — closed-alphabet-as-undeclared-type (REVIEW verdict)."""
from __future__ import annotations

from pathlib import Path

from slop.finding import Action, Disposition, Severity
from slop.rules import RULE_REGISTRY
from slop.rules.sprawl import SprawlRule
from slop.scope import scan_corpus
from slop.scope.identity import ScopeKind

# python/java/csharp recur across {extract, walk} → an undeclared "language" type.
ALPHABET = '''\
def python_extract(): pass
def python_walk(): pass
def java_extract(): pass
def java_walk(): pass
def csharp_extract(): pass
def csharp_walk(): pass
'''


def test_default_config():
    rc = SprawlRule.default_config()
    assert SprawlRule.altitudes == frozenset({ScopeKind.CORPUS})
    assert rc.param("min_alphabet") == 3


def test_registered():
    assert any(isinstance(r, SprawlRule) for r in RULE_REGISTRY)


def test_fires_on_closed_alphabet(tmp_path: Path):
    (tmp_path / "g.py").write_text(ALPHABET)
    corpus = scan_corpus(tmp_path, config=None)
    findings = list(SprawlRule().check(corpus, SprawlRule.default_config()))
    assert findings
    f = findings[0]
    assert f.disposition is Disposition.VERDICT
    assert f.action is Action.REVIEW
    assert f.severity is Severity.WARNING
    assert set(f.metadata["extent"]) == {"python", "java", "csharp"}


def test_silent_without_alphabet(tmp_path: Path):
    (tmp_path / "g.py").write_text(
        "def load(): pass\ndef compute_total(): pass\ndef render_widget(): pass\n"
    )
    corpus = scan_corpus(tmp_path, config=None)
    assert list(SprawlRule().check(corpus, SprawlRule.default_config())) == []
