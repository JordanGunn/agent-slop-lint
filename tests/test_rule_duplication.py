"""duplicate-code: Type-2 clone clusters, one violation per cluster."""
from __future__ import annotations

from pathlib import Path

from slop.config import RuleConfig
from slop.rules import RULE_REGISTRY
from slop.rules.duplication import DuplicationRule
from slop.scope import scan_corpus
from slop.scope.identity import ScopeKind

# alpha and beta are structurally identical (same AST leaf-type fingerprint),
# differing only in identifiers: a Type-2 clone pair. gamma is different.
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


def _check(corpus, **options):
    cfg = RuleConfig(name=DuplicationRule.name, options=options) if options \
        else DuplicationRule.default_config()
    return list(DuplicationRule().check(corpus, cfg))


def test_default_config_is_corpus_altitude():
    rc = DuplicationRule.default_config()
    assert rc.options == {"min_leaf_nodes": 10}
    assert DuplicationRule.altitudes == frozenset({ScopeKind.CORPUS})


def test_registered():
    assert any(isinstance(r, DuplicationRule) for r in RULE_REGISTRY)


def test_one_violation_per_cluster_at_first_member(tmp_path: Path):
    [v] = _check(_corpus(tmp_path, CLONES))
    assert v.rule == "duplicate-code"
    assert v.path == str(tmp_path / "m.py")
    assert v.line == 1
    assert v.value == 2 and v.threshold == 2
    assert "m.py:1 m.alpha" in v.message and "m.py:8 m.beta" in v.message
    assert "gamma" not in v.message


def test_min_leaf_nodes_filters_small_clones(tmp_path: Path):
    corpus = _corpus(tmp_path, CLONES)
    assert len(_check(corpus, min_leaf_nodes=5)) == 1
    assert _check(corpus, min_leaf_nodes=1000) == []


def test_silent_without_clones(tmp_path: Path):
    assert _check(_corpus(tmp_path, NO_CLONES)) == []


def test_same_named_modules_clones_listed_by_path(tmp_path: Path):
    body = CLONES.split("def gamma")[0]
    for pkg in ("a", "b"):
        (tmp_path / pkg).mkdir()
        (tmp_path / pkg / "__init__.py").write_text("")
        (tmp_path / pkg / "x.py").write_text(body.replace("alpha", f"alpha_{pkg}")
                                             .replace("beta", f"beta_{pkg}"))
    vs = _check(scan_corpus(tmp_path, config=None))
    assert len(vs) == 1
    [v] = vs
    assert v.path == str(tmp_path / "a" / "x.py")
    assert v.value == 4
    for ref in ("a/x.py:1 ", "a/x.py:8 ", "b/x.py:1 ", "b/x.py:8 "):
        assert ref in v.message
