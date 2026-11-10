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
from slop.scope import scan_corpus
from slop.scope.identity import ScopeKind

_CLONE_BODY = (
    "    a = 1\n    b = 2\n    c = a + b\n    d = c * 2\n"
    "    e = d - a\n    f = e + b\n    g = f * c\n    return g + a + b + c + d\n"
)


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
