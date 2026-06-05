"""Regression guard for the dispatch-altitude != finding-altitude invariant.

A corpus-altitude rule runs over the whole corpus (it needs corpus-wide data to
compute), but each finding is *about* a sub-scope. Findings must attribute to the
narrowest scope that contains what they are about — the entity for a single-entity
rule, the narrowest common ancestor for a group — never blanket-pinned to the
corpus. Before the locus fix every lexical/clone finding collapsed onto the corpus
root with no line, which defeated navigation and cross-rule convergence.
"""
from __future__ import annotations

from pathlib import Path

from slop.rules.duplication import DuplicationRule
from slop.rules.stutter import StutterRule
from slop.scope import scan_corpus
from slop.scope.identity import ScopeKind

_CLONE_BODY = (
    "    a = 1\n    b = 2\n    c = a + b\n    d = c * 2\n"
    "    e = d - a\n    f = e + b\n    g = f * c\n    return g + a + b + c + d\n"
)


def test_stutter_attributes_to_the_offending_entity(tmp_path: Path):
    # 'load_config' / 'save_config' restate their module 'config'.
    (tmp_path / "config.py").write_text(
        "def load_config():\n    return 1\n"
        "def save_config():\n    return 2\n"
    )
    corpus = scan_corpus(tmp_path, config=None)
    findings = list(StutterRule().check(corpus, StutterRule.default_config()))
    assert findings, "fixture should stutter"
    for f in findings:
        assert f.component.kind is not ScopeKind.CORPUS
        assert f.component.kind in (ScopeKind.CALLABLE, ScopeKind.CLASS)
        assert f.line, "a localized stutter finding carries a line"


def test_duplication_attributes_below_corpus(tmp_path: Path):
    # Two structurally identical bodies in two modules of one (root) package.
    (tmp_path / "a.py").write_text(f"def alpha():\n{_CLONE_BODY}")
    (tmp_path / "b.py").write_text(f"def beta():\n{_CLONE_BODY}")
    corpus = scan_corpus(tmp_path, config=None)
    findings = list(DuplicationRule().check(corpus, DuplicationRule.default_config()))
    assert findings, "fixture should clone"
    for f in findings:
        # The clone family lives in the root package, not 'the whole corpus'.
        assert f.component.kind is not ScopeKind.CORPUS
